# 0002. Replay recipes by label; call the model only for pages that changed

**Context.** A model on every step survives retailer changes but costs a call per action, is slow, and makes its
measured mistakes on every page. Scripts recorded by element id are free and fast until the first change.

**Decision.** For each retailer the pilot keeps recipes keyed by a page fingerprint (URL and the roles and labels
of its controls). A known page is replayed by label, so new ids do not matter. An unknown page, or a recipe whose
labels are gone, goes to the model, and the steps that moved the checkout forward become the new recipe. Recorded
steps always set the size, so a recipe never inherits a page's default.

**Consequences.** Model cost falls by two to three orders of magnitude against the model alone. Without guards a
recipe can freeze a model mistake (an add-on it missed), which is why guards are not optional (see the ablation).
