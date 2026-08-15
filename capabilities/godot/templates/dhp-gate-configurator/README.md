# DHP Gate Configurator Prototype v0.3

Zero-dollar-first Godot vertical slice for DHP interactive sales engineering. Godot is a visualization/runtime consumer, not the business source of truth.

## Current capability

- data-driven 1/2/4-leaf gates
- width/height constraints from PRODUCT_DB snapshots
- MATERIAL_DB color/material visualization metadata
- ACCESSORY_DB and IMAGE_DB IDs
- orbit/zoom camera
- Web + Windows export presets
- JSON configuration output
- Web -> Godot configuration input
- Godot -> Web `dhp-configurator-change` events
- optional DHP-AIOS live JSON adapter with allowlist, timeout, schema validation and local cache
- deterministic local snapshot fallback

## Business contract

Runtime schema: `dhp.configurator.gate.v1`.

Godot emits product/material/color/accessory/reference IDs plus dimensions. It never embeds authoritative prices. `ESTIMATION_DB` remains the pricing source of truth and Proposal/CRM consume the emitted configuration.

## Input modes

Default mode is offline/local snapshots under `res://data/`. `sources.json` may enable `external_adapters.dhp_aios` when a real DHP-AIOS endpoint exists.

For live mode set only trusted values:

```json
{
  "enabled": true,
  "base_url": "https://your-dhp-aios.example",
  "allowed_domains": ["your-dhp-aios.example"]
}
```

The adapter accepts only the declared snapshot schemas, caches successful responses under `user://dhp-configurator-cache`, and falls back to cache/local data on failure. Do not put secrets in Godot source or Web exports.

## Web bridge

Host listens for configuration changes:

```js
window.addEventListener('dhp-configurator-change', (event) => {
  const configuration = event.detail;
  // send to DHP-AIOS / ESTIMATION_DB / Proposal
});
```

Host can push a configuration into the Web export through the `dhp-configurator-host-config` bridge contract. The payload must use `dhp.configurator.gate.v1`.

## Run locally

```python
from capabilities.godot.adapter import GodotAdapter

adapter = GodotAdapter()
project = "capabilities/godot/templates/dhp-gate-configurator"
adapter.test_project(project)
```

## Export

```python
adapter.export_web(project, f"{project}/build/web/index.html", preset="Web")
adapter.export_desktop(project, f"{project}/build/windows/DHP-Gate-Configurator.exe", preset="Windows Desktop")
```

## Integration target

```text
AI Chat
  -> PRODUCT_DB / MATERIAL_DB / ACCESSORY_DB / IMAGE_DB
  -> DHP-AIOS signed/validated snapshots (optional)
  -> Godot realtime configurator
  -> dhp.configurator.gate.v1
  -> ESTIMATION_DB
  -> Proposal / Survey / Quote / Contract
```

The main Next.js website must lazy-load a Web export only when the configurator is opened. Godot remains an optional capability, never a mandatory website-core dependency.
