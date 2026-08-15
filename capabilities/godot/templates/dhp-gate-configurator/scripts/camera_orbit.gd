extends Camera3D
class_name DHPOrbitCamera

@export var target := Vector3.ZERO
@export var distance := 8.8
@export var yaw_deg := 0.0
@export var pitch_deg := -12.0
@export var min_distance := 4.0
@export var max_distance := 16.0

var dragging := false
var last_mouse := Vector2.ZERO

func _ready() -> void:
	_update_camera()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			dragging = event.pressed
			last_mouse = event.position
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = max(min_distance, distance - 0.6); _update_camera()
		elif event.pressed and event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = min(max_distance, distance + 0.6); _update_camera()
	elif event is InputEventMouseMotion and dragging:
		var delta := event.position - last_mouse
		last_mouse = event.position
		yaw_deg -= delta.x * 0.25
		pitch_deg = clamp(pitch_deg - delta.y * 0.20, -65.0, 25.0)
		_update_camera()

func frame_gate(width_m: float, height_m: float) -> void:
	target = Vector3(0, height_m * 0.45, 0)
	distance = clamp(max(width_m * 1.65, height_m * 2.5), min_distance, max_distance)
	_update_camera()

func _update_camera() -> void:
	var yaw := deg_to_rad(yaw_deg)
	var pitch := deg_to_rad(pitch_deg)
	var offset := Vector3(sin(yaw) * cos(pitch), -sin(pitch), cos(yaw) * cos(pitch)) * distance
	global_position = target + offset
	look_at(target, Vector3.UP)
