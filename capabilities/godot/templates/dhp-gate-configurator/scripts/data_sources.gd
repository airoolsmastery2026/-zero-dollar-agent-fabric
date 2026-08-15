extends RefCounted
class_name DHPDataSources

const REGISTRY := "res://data/sources.json"

static func load_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		push_error("DHP input source missing: " + path)
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Cannot open DHP input source: " + path)
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if parsed == null:
		push_error("Invalid JSON input source: " + path)
		return {}
	return parsed

static func load_registry() -> Dictionary:
	var value = load_json(REGISTRY)
	return value if value is Dictionary else {}

static func load_all() -> Dictionary:
	var registry := load_registry()
	var sources: Dictionary = registry.get("sources", {})
	var result := {"registry": registry}
	for key in sources.keys():
		result[key] = load_json(str(sources[key]))
	return result

static func index_by_id(snapshot: Variant) -> Dictionary:
	var index := {}
	if snapshot is Dictionary:
		for item in snapshot.get("items", []):
			if item is Dictionary and item.has("id"):
				index[str(item.id)] = item
	return index
