# Teach-Back

Key concepts and 2–4 questions after each milestone. Answer here or in chat; the next milestone starts only when the team says they understand. See rule 4 in [HOW_WE_BUILD.md](HOW_WE_BUILD.md).

Template:

```
## M# — <name>

**Key concepts**
- ...

**Questions**
1. ...
   - Answer:
```

---

## M0 — Foundation

**Key concepts**
- **A contract before code.** `schema.py` defines exactly what the backend returns. Backend and frontend build against it in parallel, and the frontend can work on fake data today.
- **One source of truth, exported.** The Pydantic models are the source; `contract/*.schema.json` is generated from them; the frontend's TypeScript types will be generated from that. A test fails if the generated files fall behind.
- **Validate at the edge.** Untrusted input (the drawn polygon) is checked before anything expensive happens.
- **Consistency rules in the contract.** `match_quality` must agree with `sigma`, analogs must be sorted, and `novel_climate` must agree with the best sigma, so a bug can't produce a result that contradicts itself.
- **Deterministic fake data.** A fixed random seed means regenerating the fixture gives the identical file, so it can be tested like code.

**Questions**
1. The frontend developer wants to rename `sigma` to `score`. Which files have to change, and what tells you if you forgot one?
   - Answer:
2. Why does the contract reject unknown fields instead of ignoring them?
   - Answer:
3. An analog arrives with `sigma: 1.5` and `match_quality: "strong"`. What happens, and why is that better than letting it through?
   - Answer:
4. Why is every fake result marked `source: "fixture"`?
   - Answer:

