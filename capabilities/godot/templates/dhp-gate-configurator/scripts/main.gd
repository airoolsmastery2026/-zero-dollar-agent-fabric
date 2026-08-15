extends Node3D

const PRODUCT_ID := "gate.standard.double-leaf"
const MATERIAL_PRESETS := {
	"Powder Coated Steel": "material.steel.powder-coated",
	"Aluminum": "material.aluminum.standard",
	"Wood Look": "material.finish.wood-look"
}
const COLOR_PRESETS := {
	"Anthracite": Color("#34383d"),
	"Black": Color("#111315"),
	"Warm Brown": Color("#654b38")
}
const ACCESSORY_PRESETS := {
	"None": "accessory.none",
	"Decorative Slats": "accessory.slats.vertical",
	"Glass Accent": "accessory.glass.accent"
}

@onready var gate_root: Node3D = $GateRoot
@onready var width_slider: HSlider = $UI/Panel/VBox/Width
@onready var height_slider: HSlider = $UI/Panel/VBox/Height
@onready var material_select: OptionButton = $UI/Panel/VBox/Material
@onready var color_select: OptionButton = $UI/Panel/VBox/Color
@onready var accessory_select: OptionButton = $UI/Panel/VBox/Accessory
@onready var status_label: Label = $UI/Panel/VBox/Status

var config := {
	"schema": "dhp.configurator.gate.v1",
	"product_id": PRODUCT_ID,
	"width_m": 4.0,
	"height_m": 2.2,
	"material_id": "material.steel.powder-coated",
	"color_id": "color.anthracite",
	"accessory_ids": [],
	"pricing": {"source": "ESTIMATION_DB", "embedded_price": false}
}

func _ready() -> void:
	for label in MATERIAL_PRESETS.keys(): material_select.add_item(label)
	for label in COLOR_PRESETS.keys(): color_select.add_item(label)
	for label in ACCESSORY_PRESETS.keys(): accessory_select.add_item(label)
	width_slider.value_changed.connect(_on_dimensions_changed)
	height_slider.value_changed.connect(_on_dimensions_changed)
	material_select.item_selected.connect(_on_material_changed)
	color_select.item_selected.connect(_on_color_changed)
	accessory_select.item_selected.connect(_on_accessory_changed)
	$UI/Panel/VBox/Export.pressed.connect(_export_configuration)
	_rebuild_gate()

func _on_dimensions_changed(_value: float) -> void:
	config.width_m = snapped(width_slider.value, 0.1)
	config.height_m = snapped(height_slider.value, 0.1)
	_rebuild_gate()

func _on_material_changed(index: int) -> void:
	config.material_id = MATERIAL_PRESETS[material_select.get_item_text(index)]
	_rebuild_gate()

func _on_color_changed(index: int) -> void:
	var label := color_select.get_item_text(index)
	config.color_id = "color." + label.to_lower().replace(" ", "-")
	_rebuild_gate()

func _on_accessory_changed(index: int) -> void:
	var id: String = ACCESSORY_PRESETS[accessory_select.get_item_text(index)]
	config.accessory_ids = [] if id == "accessory.none" else [id]
	_rebuild_gate()

func _rebuild_gate() -> void:
	for child in gate_root.get_children(): child.queue_free()
	var width: float = config.width_m
	var height: float = config.height_m
	var frame := _box(Vector3(width, 0.08, 0.08), Vector3(0, height / 2.0, 0), Color("#25282c"))
	gate_root.add_child(frame)
	gate_root.add_child(_box(Vector3(0.08, height, 0.08), Vector3(-width / 2.0, 0, 0), Color("#25282c")))
	gate_root.add_child(_box(Vector3(0.08, height, 0.08), Vector3(width / 2.0, 0, 0), Color("#25282c")))
	var leaf_color: Color = COLOR_PRESETS[color_select.get_item_text(color_select.selected)] if color_select.item_count > 0 else Color("#34383d")
	var slat_count := max(8, int(width * 5.0))
	for i in range(slat_count):
		var x := -width / 2.0 + (i + 0.5) * width / slat_count
		gate_root.add_child(_box(Vector3(width / slat_count * 0.72, height * 0.92, 0.035), Vector3(x, 0, 0), leaf_color))
	status_label.text = "%.1fm × %.1fm | %s | %s" % [width, height, config.material_id, config.color_id]

func _box(size: Vector3, position: Vector3, color: Color) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = 0.55
	material.roughness = 0.32
	mesh.material = material
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.position = position
	return node

func _export_configuration() -> void:
	var payload := JSON.stringify(config, "  ")
	status_label.text = payload
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log(" + JSON.stringify(payload) + ")")
	else:
		var path := "user://dhp-gate-configuration.json"
		var file := FileAccess.open(path, FileAccess.WRITE)
		if file:
			file.store_string(payload)
			status_label.text = "Saved: " + ProjectSettings.globalize_path(path)
