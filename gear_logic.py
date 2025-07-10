import math
import csv

MAX_GEARS = 24
RPM_STEP = 100
MIN_RPM = 500

def calc_wheel_diameter_m(specs_or_diameter, width=None, aspect=None, rim=None, diameter=None, unit='in'):
    """
    Calculate wheel diameter in meters from either:
    - specs: width (mm), aspect (%), rim (inches)
    - diameter: direct tire diameter (inches or mm)
    """
    if specs_or_diameter == 'specs':
        section_height = (width / 25.4) * (aspect / 100)
        tire_diameter = (2 * section_height) + rim
    else:
        tire_diameter = diameter / 25.4 if unit == 'mm' else diameter
    return tire_diameter * 0.0254

def gear_speed_table(wheel_diameter_m, final_drive, max_rpm, gear_ratios, speed_unit):
    """
    Returns (rpm_values, gear_speeds) where gear_speeds is a list-of-lists, one per gear.
    Each gear's list contains the speed (in unit) at each RPM step.
    """
    speed_factor = 1 if speed_unit == "km/h" else 0.621371
    rpm_values = list(range(MIN_RPM, max_rpm + 1, RPM_STEP))
    table = []
    for gr in gear_ratios:
        speeds = []
        for rpm in rpm_values:
            if gr == 0 or final_drive == 0:
                speed = 0
            else:
                wheel_rpm = rpm / (gr * final_drive)
                speed_kmh = (wheel_rpm * math.pi * wheel_diameter_m * 60) / 1000
                speed = speed_kmh * speed_factor
            speeds.append(speed)
        table.append(speeds)
    return rpm_values, table

def export_csv(filepath, headers, table_data):
    """Export the table to a CSV file."""
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(table_data)
