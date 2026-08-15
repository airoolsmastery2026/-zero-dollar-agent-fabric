extends Node3D

@onready var gate_root: Node3D = $GateRoot
@onready var product_select: OptionButton = $UI/Panel/VBox/Product
@onready var width_slider: HSlider = $UI/Panel/VBox/Width
@onready var height_slider: HSlider = $UI/Panel/VBox/Height
@onready var material_select: OptionButton = $UI/Panel/VBox/Material
@onready var color_select: OptionButton = $UI/Panel/VBox/Color
@onready var accessory_select: OptionButton = $UI/Panel/VBox/Accessory
@onready var source_status: Label = $UI/Panel/VBox/SourceStatus
@onready var status_label: Label = $UI/Panel/VBox/Status

var sources := {}
var products: Array = []
var materials: Array = []
var colors: Array = []
var accessories: Array = []
var product_index := {}
var material_index := {}
var accessory_index := {}
var color_index := {}

var config := {
	"schema": "dhp.configurator.gate.v1",
	"product_id": "gate.standard.double-leaf",
	"width_m": 4.0,
	"height_m": 2.2,
	"material_id": "material.steel.powder-coated",
	"color_id": "color.anthracite",
	"accessory_ids": [],
	"reference_image_ids": [],
	"pricing": {"source": "ESTIMATION_DB", "embedded_price": false}
}

func _ready() -> void:
	_load_input_sources()
	_bind_controls()
	_apply_initial_configuration()
	_rebuild_gate()

func _load_input_sources() -> void:
	sources = DHPDataSources.load_all()
	products = sources.get("products", {}).get("items", [])
	materials = sources.get("materials", {}).get("items", [])
	colors = sources.get("materials", {}).get("colors", [])
	accessories = sources.get("accessories", {}).get("items", [])
	product_index = DHPDataSources.index_by_id(sources.get("products", {}))
	material_index = DHPDataSources.index_by_id(sources.get("materials", {}))
	accessory_index = DHPDataSources.index_by_id(sources.get("accessories", {}))
	for item in colors:
		color_index[str(item.get("id", ""))] = item
	_fill_options(product_select, products)
	_fill_options(material_select, materials)
	_fill_options(color_select, colors)
	_fill_options(accessory_select, accessories)
	var image_count: int = sources.get("images", {}).get("items", []).size()
	source_status.text = "Sources: %d products • %d materials • %d colors • %d accessories • %d images" % [products.size(), materials.size(), colors.size(), accessories.size(), image_count]

func _fill_options(control: OptionButton, items: Array) -> void:
	control.clear()
	for item in items:
		control.add_item(str(item.get("label", item.get("id", "item"))))
		control.set_item_metadata(control.item_count - 1, str(item.get("id", "")))

func _bind_controls() -> void:
	product_select.item_selected.connect(_on_product_changed)
	width_slider.value_changed.connect(_on_dimensions_changed)
	height_slider.value_changed.connect(_on_dimensions_changed)
	material_select.item_selected.connect(_on_material_changed)
	color_select.item_selected.connect(_on_color_changed)
	accessory_select.item_selected.connect(_on_accessory_changed)
	$UI/Panel/VBox/Export.pressed.connect(_export_configuration)

func _apply_initial_configuration() -> void:
	var initial = sources.get("initial_configuration", {})
	if initial is Dictionary and not initial.is_empty():
		config.merge(initial, true)
	_select_id(product_select, str(config.product_id))
	_select_id(material_select, str(config.material_id))
	_select_id(color_select, str(config.color_id))
	var accessory_ids: Array = config.get("accessory_ids", [])
	_select_id(accessory_select, str(accessory_ids[0]) if not accessory_ids.is_empty() else "accessory.none")
	width_slider.value = float(config.width_m)
	height_slider.value = float(config.height_m)
	_apply_product_constraints()

func _select_id(control: OptionButton, target_id: String) -> void:
	for index in range(control.item_count):
		if str(control.get_item_metadata(index)) == target_id:
			control.select(index)
			return

func _on_product_changed(index: int) -> void:
	config.product_id = str(product_select.get_item_metadata(index))
	_apply_product_constraints()
	_rebuild_gate()

func _apply_product_constraints() -> void:
	var product: Dictionary = product_index.get(str(config.product_id), {})
	if product.is_empty(): return
	width_slider.min_value = float(product.get("min_width_m", 0.9))
	width_slider.max_value = float(product.get("max_width_m", 6.0))
	config.width_m = clamp(float(config.width_m), width_slider.min_value, width_slider.max_value)
	width_slider.value = float(config.width_m)

func _on_dimensions_changed(_value: float) -> void:
	config.width_m = snapped(width_slider.value, 0.1)
	config.height_m = snapped(height_slider.value, 0.1)
	_rebuild_gate()

func _on_material_changed(index: int) -> void:
	config.material_id = str(material_select.get_item_metadata(index))
	_rebuild_gate()

func _on_color_changed(index: int) -> void:
	config.color_id = str(color_select.get_item_metadata(index))
	_rebuild_gate()

func _on_accessory_changed(index: int) -> void:
	var id := str(accessory_select.get_item_metadata(index))
	config.accessory_ids = [] if id == "accessory.none" else [id]
	_rebuild_gate()

func _rebuild_gate() -> void:
	for child in gate_root.get_children(): child.queue_free()
	var width := float(config.width_m)
	var height := float(config.height_m)
	var product: Dictionary = product_index.get(str(config.product_id), {})
	var leaf_count := int(product.get("leaf_count", 2))
	var color_data: Dictionary = color_index.get(str(config.color_id), {})
	var leaf_color := Color(str(color_data.get("hex", "#34383d")))
	var material_data: Dictionary = material_index.get(str(config.material_id), {})
	var metallic := float(material_data.get("metallic", 0.55))
	var roughness := float(material_data.get("roughness", 0.32))

	gate_root.add_child(_box(Vector3(width, 0.08, 0.08), Vector3(0, height / 2.0, 0), Color("#25282c"), 0.7, 0.25))
	gate_root.add_child(_box(Vector3(0.08, height, 0.08), Vector3(-width / 2.0, 0, 0), Color("#25282c"), 0.7, 0.25))
	gate_root.add_child(_box(Vector3(0.08, height, 0.08), Vector3(width / 2.0, 0, 0), Color("#25282c"), 0.7, 0.25))

	var slat_count := max(8, int(width * 5.0))
	for i in range(slat_count):
		var x := -width / 2.0 + (i + 0.5) * width / slat_count
		gate_root.add_child(_box(Vector3(width / slat_count * 0.72, height * 0.92, 0.035), Vector3(x, 0, 0), leaf_color, metallic, roughness))

	for leaf in range(1, leaf_count):
		var separator_x := -width / 2.0 + width * float(leaf) / float(leaf_count)
		gate_root.add_child(_box(Vector3(0.035, height * 0.92, 0.055), Vector3(separator_x, 0, -0.01), Color("#202225"), 0.7, 0.25))

	status_label.text = "%s • %.1fm × %.1fm • %s • %s" % [config.product_id, width, height, config.material_id, config.color_id]

func _box(size: Vector3, position: Vector3, color: Color, metallic: float, roughness: float) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = roughness
	mesh.material = material
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.position = position
	return node

func _export_configuration() -> void:
	var payload := JSON.stringify(config, "  ")
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.dispatchEvent(new CustomEvent('dhp-configurator-change',{detail:" + payload + "}));")
		status_label.text = "Configuration event emitted to Web host"
	else:
		var path := "user://dhp-gate-configuration.json"
		var file := FileAccess.open(path, FileAccess.WRITE)
		if file:
			file.store_string(payload)
			status_label.text = "Saved: " + ProjectSettings.globalize_path(path)
