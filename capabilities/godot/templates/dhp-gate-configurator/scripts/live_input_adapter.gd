extends Node
class_name DHPLiveInputAdapter

signal snapshot_loaded(payload: Dictionary, source: String)
signal snapshot_failed(message: String)

const CACHE_DIR := "user://dhp-configurator-cache"
const DEFAULT_TIMEOUT_SEC := 8.0

var registry: Dictionary = {}
var adapter: Dictionary = {}
var _http: HTTPRequest
var _request_key := ""

func _ready() -> void:
	_http = HTTPRequest.new()
	add_child(_http)
	_http.timeout = DEFAULT_TIMEOUT_SEC
	_http.request_completed.connect(_on_request_completed)

func configure(source_registry: Dictionary) -> void:
	registry = source_registry
	adapter = registry.get("external_adapters", {}).get("dhp_aios", {})

func enabled() -> bool:
	return bool(adapter.get("enabled", false)) and not str(adapter.get("base_url", "")).is_empty()

func refresh_snapshot(key: String) -> void:
	_request_key = key
	if not enabled():
		_emit_cached_or_fail(key, "Live adapter disabled")
		return
	var endpoint_map: Dictionary = adapter.get("endpoints", {})
	var endpoint := str(endpoint_map.get(key, ""))
	if endpoint.is_empty():
		_emit_cached_or_fail(key, "No endpoint configured for " + key)
		return
	var base_url := str(adapter.get("base_url", "")).trim_suffix("/")
	var url := base_url + "/" + endpoint.trim_prefix("/")
	if not _allowed(url):
		_emit_cached_or_fail(key, "Blocked by source allowlist")
		return
	_http.timeout = float(adapter.get("timeout_sec", DEFAULT_TIMEOUT_SEC))
	var headers := PackedStringArray(["Accept: application/json"])
	var err := _http.request(url, headers, HTTPClient.METHOD_GET)
	if err != OK:
		_emit_cached_or_fail(key, "HTTP request failed to start")

func _allowed(url: String) -> bool:
	var allowed: Array = adapter.get("allowed_domains", [])
	if allowed.is_empty(): return false
	var host := url.get_slice("/", 2).split(":")[0].to_lower()
	for item in allowed:
		if host == str(item).to_lower(): return true
	return false

func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_emit_cached_or_fail(_request_key, "Live source HTTP %s" % response_code)
		return
	var parsed = JSON.parse_string(body.get_string_from_utf8())
	if not (parsed is Dictionary) or not _valid_snapshot(_request_key, parsed):
		_emit_cached_or_fail(_request_key, "Invalid live source schema")
		return
	_write_cache(_request_key, parsed)
	snapshot_loaded.emit(parsed, "live")

func _valid_snapshot(key: String, payload: Dictionary) -> bool:
	var expected: Dictionary = adapter.get("schemas", {})
	var expected_schema := str(expected.get(key, ""))
	if expected_schema.is_empty(): return false
	return str(payload.get("schema", "")) == expected_schema and payload.get("items", []) is Array

func _cache_path(key: String) -> String:
	return CACHE_DIR + "/" + key + ".json"

func _write_cache(key: String, payload: Dictionary) -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CACHE_DIR))
	var file := FileAccess.open(_cache_path(key), FileAccess.WRITE)
	if file: file.store_string(JSON.stringify(payload))

func _read_cache(key: String) -> Dictionary:
	var path := _cache_path(key)
	if not FileAccess.file_exists(path): return {}
	var file := FileAccess.open(path, FileAccess.READ)
	var parsed = JSON.parse_string(file.get_as_text()) if file else null
	return parsed if parsed is Dictionary else {}

func _emit_cached_or_fail(key: String, message: String) -> void:
	var cached := _read_cache(key)
	if not cached.is_empty():
		snapshot_loaded.emit(cached, "cache")
	else:
		snapshot_failed.emit(message)
