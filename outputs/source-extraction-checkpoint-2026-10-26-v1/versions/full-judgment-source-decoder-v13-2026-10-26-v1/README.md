# V13 hosted decoder repair and staged validation

V11 returned its first response in 51.63 seconds. The corresponding V12 request
has 792 additional maxItems constraints in the hosted decoder and corresponding
prompt schema text. Three identical V12 attempts timed out before HTTP response.
This is a strong candidate regression, not knowledge of the provider internals.

V13 removes only maxItems=N on an array with uniqueItems=true and N distinct
allowed string values from the hosted schema. The bound is logically implied by
uniqueness and enum membership. The full bound remains in the prompt and local
semantic validation. Streaming repeated-reference detection remains unchanged.
All other model inputs and parameters remain V12-identical. The first hosted
schema is byte-structure equivalent to the successful V11 schema. No source, ID,
interpretation, acceptance, output capacity, or 180-second socket timeout changes.

Run a staged gate on the first two existing source groups of complete judgment
1251841, with two blind readings each: four calls maximum, plus only the already
allowed known-usage technical retry. Every call receives the complete original.
These include the group where V11 entered its citation loop. This is a partial
source-reading gate, not complete extraction, full C, or independent evaluation.
No oracle records or field-level answer replacements are used. Stop at the gate,
or on failure; no repeated attempts until success and no other cases.

All old attempts, fees and reserves remain retained. Remaining authorization is
$5.57058723 under the existing six-case $6 envelope. No training, default changes,
main-thread changes, commits or pushes. A response recovery is evidence about
transport compatibility, not proof of better source interpretation or a direct
measurement of server grammar compilation time.
