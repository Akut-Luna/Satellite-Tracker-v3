from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    antenna_latitude: float
    antenna_longitude: float
    antenna_altitude: float
    local_tz: str
    motor_IP: str
    motor_port: int
    min_angle_change_before_update: float
    min_before_recalculate_flight_path: int
    flight_path_steps: int
    auto_uncheck_start_tracking_at_AOS_btn: bool
    time_resolution_horizons_state_vector: int
    time_resolution_horizons_directly: int