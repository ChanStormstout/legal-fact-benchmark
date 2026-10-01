"""Independent finite-language oracle for conditional local experiments.

Does not import the matcher, generator, canonicalizer or field projector under
test. It shares the declared input dependency contract, not its implementation.
Separate hand-expected tests check that contract. Exhaustiveness applies only to
the finite two-record grammar and observed constants, not legal pattern space.
"""
import itertools
import json
import math
from datetime import date


def encode(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def normalized(query):
    forms = []
    for arrangement in itertools.permutations(query["atoms"]):
        names = {atom["var"]: "e" + str(i) for i, atom in enumerate(arrangement)}
        atoms = [dict(atom, var=names[atom["var"]]) for atom in arrangement]
        clauses = []
        for original in query.get("constraints", []):
            clause = dict(original)
            for side in ("left", "right"):
                if side in clause:
                    name, path = clause[side].split(".", 1)
                    clause[side] = names[name] + "." + path
            if clause["op"] in ("same", "different"):
                clause["left"], clause["right"] = sorted((clause["left"], clause["right"]))
            clauses.append(clause)
        forms.append(encode({"atoms": atoms, "constraints": sorted(clauses, key=encode)}))
    return min(forms)


def lookup(record, path):
    for block in record["field_contract"]["blocked"]:
        for dependency in block["affected_fields"]:
            if dependency == "*" or path == dependency or path.startswith(dependency + "."):
                return None
    cell = record
    for key in path.split("."):
        cell = cell.get(key) if isinstance(cell, dict) else None
    return cell


def exact_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def answer(view, query):
    atoms = query["atoms"]
    pools = []
    for atom in atoms:
        pools.append([record for record in view["events"]
                      if record["unit_id"] == view["units"][0]["id"]
                      and (record["type"] == atom["type"] or record["field_contract"]["type_unresolved"])
                      and ("event_id" not in atom or atom["event_id"] == record["id"])])
    good, pending = set(), set()
    for records in itertools.product(*pools):
        env = {atom["var"]: record for atom, record in zip(atoms, records)}
        truth = []
        for atom, record in zip(atoms, records):
            for key, requirement in (("type", atom["type"]), ("status", atom.get("status", "COURT_FOUND")),
                                     ("polarity", atom.get("polarity", "POSITIVE"))):
                if requirement != "ANY":
                    cell = lookup(record, key)
                    truth.append(None if cell is None or cell == "UNDETERMINED" else cell == requirement)
        for clause in query.get("constraints", []):
            name, path = clause["left"].split(".", 1)
            left = lookup(env[name], path)
            if clause["op"] == "equals":
                right = clause["value"]
            else:
                name, path = clause["right"].split(".", 1)
                right = lookup(env[name], path)
            if left is None or right is None:
                truth.append(None)
            elif clause["op"] in ("equals", "same"):
                truth.append(type(left) is bool and type(right) is bool and left == right
                             if type(left) is bool or type(right) is bool else left == right)
            elif clause["op"] == "different":
                truth.append(not (type(left) is bool and type(right) is bool and left == right)
                             if type(left) is bool or type(right) is bool else left != right)
            elif not exact_date(left) or not exact_date(right):
                truth.append(None)
            else:
                truth.append(date.fromisoformat(left) < date.fromisoformat(right))
        binding = tuple(sorted((name, record["id"]) for name, record in env.items()))
        if False in truth:
            continue
        if None in truth:
            pending.add(binding)
        else:
            good.add(binding)
    status = ("MATCH" if good else "UNKNOWN" if pending else "MISMATCH"
              if all("event_id" in atom for atom in atoms) and all(pools) else "NOT_FOUND")
    return {"status": status, "matches": sorted(good), "unknown": sorted(pending)}


def enumerate_space(views):
    """Enumerate templates globally, then retain those with a known witness.

    Unlike production's observed-pair expansion, constructs all one/two role
    joins for each type pair, both time directions, and every observed scalar
    attribute constant. No generation budget or support pruning.
    """
    roles, attrs = {}, {}
    for view in views:
        for record in view["events"]:
            kind = lookup(record, "type")
            if kind is None or lookup(record, "status") != "COURT_FOUND" or lookup(record, "polarity") != "POSITIVE":
                continue
            roles.setdefault(kind, set())
            attrs.setdefault(kind, {})
            for key in record["roles"]:
                if lookup(record, "roles." + key) is not None:
                    roles[kind].add(key)
            for key in record["attributes"]:
                value = lookup(record, "attributes." + key)
                if isinstance(value, (str, int, float, bool)) and not (isinstance(value, float) and not math.isfinite(value)):
                    attrs[kind].setdefault(key, {})[encode(value)] = value
    templates, discovered, tested = set(), set(), 0
    for first, second in itertools.combinations_with_replacement(sorted(roles), 2):
        atoms = [{"var": "x", "type": first}, {"var": "y", "type": second}]
        links = [{"op": "same", "left": "x.roles." + a, "right": "y.roles." + b}
                 for a in sorted(roles[first]) for b in sorted(roles[second])]
        extra = [None, {"op": "before", "left": "x.time", "right": "y.time"},
                 {"op": "before", "left": "y.time", "right": "x.time"}]
        for var, kind in (("x", first), ("y", second)):
            for key in sorted(attrs[kind]):
                for encoded in sorted(attrs[kind][key]):
                    extra.append({"op": "equals", "left": var + ".attributes." + key, "value": attrs[kind][key][encoded]})
        for size in (1, 2):
            for combination in itertools.combinations(links, size):
                base = [{"op": "different", "left": "x.id", "right": "y.id"}] + list(combination)
                for extension in extra:
                    serialized = normalized({"atoms": atoms, "constraints": base + ([] if extension is None else [extension])})
                    if serialized in templates:
                        continue
                    templates.add(serialized)
                    query = json.loads(serialized)
                    tested += 1
                    if any(answer(view, query)["status"] == "MATCH" for view in views):
                        discovered.add(serialized)
    return {"templates_checked": tested, "candidates": sorted(discovered),
            "scope": "Observed types/role names/scalar constants; two distinct records; one/two ID joins; zero/one date or attribute extension"}


def check(views, candidates):
    expected = enumerate_space(views)
    proposed, truth = set(candidates), set(expected["candidates"])
    return dict(expected, missing=sorted(truth - proposed), extra=sorted(proposed - truth),
                exact=truth == proposed)
