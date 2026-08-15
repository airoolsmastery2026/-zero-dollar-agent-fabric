# DHP Gate Configurator Input Sources

The configurator is data-driven. Godot is a visualization consumer, not the business source of truth.

## Supported source classes

1. `PRODUCT_DB` snapshot -> product IDs, leaf count, dimensional constraints.
2. `MATERIAL_DB` snapshot -> material IDs and visual properties.
3. `ACCESSORY_DB` snapshot -> accessory IDs and display metadata.
4. `IMAGE_DB` snapshot -> reference-image IDs/URIs/tags.
5. Initial configuration JSON -> project/customer-specific starting state.
6. Future DHP-AIOS HTTP adapter -> signed JSON snapshots from server APIs.

`PRICE_DB` / `ESTIMATION_DB` are intentionally not loaded as render-time price truth. Godot emits configuration IDs; estimation services calculate price outside the engine.

## Registry

`res://data/sources.json` maps logical source names to local JSON resources. Local snapshots make the prototype deterministic, offline-capable and zero-dollar-first.

The registry also reserves an `external_adapters.dhp_aios` contract. It is disabled by default. Remote HTTP sources must use an allowlist and validated schemas before activation.

## Web host event

A Web export emits:

`dhp-configurator-change`

with the complete `dhp.configurator.gate.v1` object in `event.detail`. DHP Web/LuxRender can listen for this event, send it to `ESTIMATION_DB`, and update Proposal/CRM without coupling business rules to Godot.

## Input evolution

Prototype v0.2: local JSON snapshots.

Next: DHP-AIOS adapter -> fetch signed product/material/image snapshots -> cache locally -> validate schema -> hydrate Godot -> emit configuration events.
