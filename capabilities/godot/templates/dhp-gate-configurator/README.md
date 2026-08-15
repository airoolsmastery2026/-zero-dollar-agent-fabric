# DHP Gate Configurator Prototype

A zero-dollar-first Godot vertical slice for Đại Hải Phát interactive sales engineering.

## Scope

This prototype is intentionally not a pricing engine and not part of a web framework core. It visualizes a gate configuration and emits a stable configuration contract that downstream DHP services can send to `ESTIMATION_DB`, Proposal, CRM, or quotation workflows.

Current controls:
- gate width: 2.0–6.0 m
- gate height: 1.5–3.0 m
- material preset IDs
- color presets
- accessory preset IDs
- Web and Windows export presets
- JSON configuration output

## Contract

The runtime emits schema `dhp.configurator.gate.v1` with IDs such as `product_id`, `material_id`, `color_id`, and `accessory_ids`. Price is never embedded in GDScript. `pricing.source` points to `ESTIMATION_DB` as the business source of truth.

## Run locally

Open the folder in Godot 4.x and run `main.tscn`, or use the Zero-Dollar Agent Fabric adapter:

```python
from capabilities.godot.adapter import GodotAdapter

adapter = GodotAdapter()
project = "capabilities/godot/templates/dhp-gate-configurator"
adapter.test_project(project)
```

## Export

With matching Godot export templates installed locally:

```python
adapter.export_web(project, f"{project}/build/web/index.html", preset="Web")
adapter.export_desktop(project, f"{project}/build/windows/DHP-Gate-Configurator.exe", preset="Windows Desktop")
```

## DHP integration target

```text
AI Chat
  -> PRODUCT_DB / MATERIAL_DB / IMAGE_DB
  -> dhp.configurator.gate.v1
  -> Godot realtime visualization
  -> configuration changed event
  -> ESTIMATION_DB
  -> Proposal / Survey / Quote / Contract
```

The web application should lazy-load a Web export only when the user opens the configurator. Do not make Godot a mandatory dependency of the main DHP website bundle.
