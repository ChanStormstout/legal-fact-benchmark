# Diagnosis and acceptance limits

## Why the earlier offline review missed the defect

The prior compactor detected a schema by looking for keys such as `type`. A
properties map can itself contain a field literally named `type`; factoring that
map made the displayed schema invalid. The custom inverse transformation still
reconstructed the original dictionary, so round-trip equality passed. An inverse
using the same assumption is insufficient independent verification. The hosted
decoder received the uncompressed contract, creating two different instructions.

V11's complete cached-call audit checks the displayed schema and actual decoder
schema with a separately implemented JSON Schema validator, in addition to exact
round-trip equality and validation of full cached outputs. Twenty-four preserved
V10 displayed schemas failed that independent schema check. This establishes a
prompt-generation defect. Its share of model omissions has not been isolated in a
controlled ablation and is not claimed as the sole cause.

## Other observed failures

V10 allowed empty global records while coverage said material was captured. Models
also placed extracted facts in coverage explanations, misread supplied unit maps,
or cited heading lines for substantive propositions. No original passage was
missing from the inspected actual request. Correct raw text availability does not
establish that the representation is easy to use or that the model understood it.

V9 repeated propositions and blurred narrated lower-court findings with current
court findings. The LatentWeaver local adaptation invented a father-son relationship
and failed a native graph relation requirement. Preserve these comparator errors;
do not fix their answers in code or modify the comparator while claiming a fair
unchanged-method comparison. V11 addresses the common source-reading requirements,
but cannot guarantee that Qwen will make no semantic mistakes.

## First-document gate

One full original, fixed model, fixed parameters, one attempt. Complete the planned
independent readings, one reconciliation pass and one final source review. Stop
after this document even if technically successful. Do not use partial outputs to
tune this frozen version or fill correct intermediate records. All calls count.

Review the whole output against the original, including important claims, relationships,
procedural scope, conditions, adverse content and final disposition. Specifically
report empty material rows, missing content described only in notes, invalid main
citations, exact duplicate aliases, remaining paraphrase repetition, and source
mistakes that survive model review. These are diagnostic categories, not oracle
inputs or a selected-field success score. Any expansion requires a source-grounded
whole-document assessment, including what remains missing and why.

The offline replay uses existing fallible V9 output for both simulated readers and
keeps every interpretation UNRESOLVED. It checks interfaces only. The 122 replay
records are not new correct labels. Old inputs and outcomes remain byte-identical.
The installed JSON Schema validator lives only inside this independent directory;
no shared runtime packages, defaults, repository state or main experiment were changed.
