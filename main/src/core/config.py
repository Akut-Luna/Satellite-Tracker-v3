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

    # DISPLAY_LIGHT_TIME_CORRECTION_OPTION
    # DISPLAY_HORIZONS_DIRECTLY_OPTION
    # AUTO_UNCHECK_START_TRACKING_AT_AOS_BTN