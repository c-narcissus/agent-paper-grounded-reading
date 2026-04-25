# Research-Generative Methodology

Use this reference when the user wants more than grounded verification.
Its purpose is to turn a paper reading into a **research-generation exercise** without relaxing any source-grounding requirement.

The core move is:

> Read the paper as a hidden design path.

Do not only ask:

> What did the paper do?

Also ask:

> What sequence of observations, broken assumptions, imported tools, blocked transfers, and narrative choices could have led to this paper?

## 1. Research Equation

Start by compressing the paper into:

`old success + broken assumption + hard setting + borrowed tool + surrogate mechanism`

Useful forms:

- `A solves P when C holds; T breaks C; M almost helps but requires Y; the paper builds Z instead.`
- `valuable field + painful assumption + emerging tool + unserved setting`

Key questions:

- What important paradigm already worked?
- What hidden assumption quietly made it work?
- In what realistic setting does that assumption fail?
- What neighboring method almost transfers?
- What missing mechanism `Y` prevents direct transfer?
- What surrogate `Z` is constructed instead?

Common replacements:

| Missing `Y` | Replacement `Z` |
|---|---|
| central server | peer consensus, gossip, graph coordination |
| labels | pseudo-labels, weak supervision, self-supervision |
| shared validation set | proxy validation, agreement score, synthetic validation |
| global data | public embeddings, prototypes, generated data |
| trusted clients | reputation, uncertainty, robust aggregation |
| aligned modalities | contrastive anchors, latent bridges, adapters |

## 2. Reconstructing How the Direction Was Found

Use evidence-backed phrasing:

- "The authors likely noticed that ..."
- "A plausible thinking path is ..."
- "The paper's setup suggests ..."

Direction-finding checklist:

1. popular paradigm
2. hidden assumption
3. realistic violation
4. tempting borrowed method
5. blocking constraint
6. replacement mechanism

The most useful author-side reconstruction usually looks like:

> Prior work in `A` is attractive because it solves `P`, but it assumes `C`.  
> In the target setting `T`, `C` is unavailable, unsafe, or unrealistic.  
> A neighboring method family `M` almost solves the problem, but it relies on `Y`, which is also unavailable under `T`.  
> The paper therefore builds `Z`, a feasible surrogate for `Y`, using only resources allowed in the target setting.

## 3. How the Authors Built the Story

Strong papers usually move through this bridge:

`challenge -> failure mode -> design principle -> module -> ablation`

Look for:

- a base problem that matters
- a standard assumption that fails
- a seemingly relevant solution family
- a missing resource that blocks direct use
- several concrete sub-problems
- one module per sub-problem
- experiments that validate both the full loop and each module

The best papers are not bags of tricks.
They often build a loop such as:

- noisy signal -> proxy resource -> better coordination -> cleaner signal
- weak supervision -> better representation -> reliability estimation -> stronger weak supervision

When possible, make the loop explicit.

## 4. Module-By-Module Author Thinking

For each module, reconstruct:

`failure + unavailable ideal + available proxy + design choice + hidden assumption + risk`

Ask:

- What goes wrong without this module?
- If the authors had unlimited access, what would they use instead?
- What proxy is still allowed under the paper's constraints?
- Why is this design better than the naive local alternative?
- What hidden bet makes the module plausible?
- What future work appears if that bet fails?

Useful framing:

> This module is best understood not as a trick, but as a surrogate for the missing mechanism `Y`.

## 5. Reverse Citation Logic

Treat citations as narrative functions, not as a bibliography list.

Typical functions:

- field anchor
- limitation evidence
- method ancestor
- neighboring-field inspiration
- strong baseline pressure
- benchmark protocol
- implementation machinery
- contrast boundary

For each important citation cluster, explain:

- what permission it gives the authors
- what assumption it carries
- what gap it leaves open
- how the current paper inherits, modifies, or rejects it

## 6. Experiments as Story Evidence

Read each experiment as:

`claim + counterfactual + metric + stress condition`

Ask:

- What claim is this experiment supporting?
- What alternative explanation does it rule out?
- What target difficulty is being stressed?
- Which module or story edge does the ablation justify?
- Does the result really support the narrative role the paper assigns to that module?

If the paper claims to solve a hard setting `T`, strong experiments usually vary the intensity of `T`.

## 7. Story Patterns Worth Reusing

Extract a reusable research pattern.
Common patterns:

### Replacement story

`Y` exists in the easy setting, but not in the hard one.  
The paper builds `Z` to play the role of `Y` without violating constraints.

### Three-module story

`F1 -> M1`, `F2 -> M2`, `F3 -> M3`

Often:

- `M1` repairs signal reliability
- `M2` enriches information
- `M3` coordinates the global system

### Two-axis empty cell

The paper lives at the intersection of two hard conditions that prior work handled separately.

### Closed-loop contribution

One module produces the missing resource that the next module needs, eventually improving the condition for the first module.

### Hidden-assumption break

The next paper emerges by making the current method work when one of its hidden assumptions fails.

## 8. Weakness to New Idea Conversion

Use:

`future work = current method + violated assumption + new mechanism`

For each important weakness, ask:

- what claim is being made
- what evidence supports it
- what evidence is missing
- what hidden assumption is required
- what happens if that assumption fails
- what new paper could be written around that failure

Common weakness buckets:

- theory gap
- scalability
- robustness
- privacy leakage
- compute cost
- proxy mismatch
- unrealistic evaluation
- shallow ablation
- fragile assumptions

## 9. Writing Rules

Prefer phrasing like:

- "A plausible author-side thinking path is ..."
- "This module is best understood as a surrogate for ..."
- "The citation is not ornamental; it functions as ..."
- "The paper's deepest lesson is the replacement pattern ..."
- "The hidden bet of this module is ..."
- "This weakness can be converted into a new research question ..."

Avoid:

- restating the abstract
- listing sections without causal explanation
- paraphrasing equations without explaining why they were needed
- treating citations as mere background
- giving generic future work
- speaking as if private author intent were directly observed

## 10. Minimal Checklist

Before finalizing, confirm:

- the broken assumption is explicit
- the unavailable mechanism `Y` is explicit
- the surrogate `Z` is explicit
- each major module is tied to a failure mode
- key citations have narrative roles
- experiments are tied to claims and counterfactuals
- at least one reusable story pattern is extracted
- hidden assumptions are converted into future research directions
- all idea-generative claims stay grounded in real source evidence
