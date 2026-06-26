import traceback
import cartopy.crs as ccrs
import cartopy.geodesic as geodesic
import numpy as np
from PySide6.QtCore import QDateTime, Qt, QTimer, QTimeZone, Signal
from PySide6.QtGui import QIcon
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas # must be imported after PySide

def update_map(self, latitude, longitude, altitude):
    '''
    Parameters:
        latitude (float): Latitude in degrees
        longitude (float): Longitude in degrees
        altitude (float): Altitude in km
    '''

    self.map_ax.clear() # Clear the previous plot but keep the axis (image)

    # if there is not satellie to plot, the flight plan must be old
    if latitude is None or longitude is None:
        self.ground_track = None 
    
    img_extent = (-180, 180, -90, 90)
    self.map_ax.imshow(self.earth_img, origin='upper', extent=img_extent, transform=self.map_projection)
    
    # plot antenna 
    self.map_ax.plot(
        self.config.antenna_longitude, 
        self.config.antenna_latitude, 
        'o', 
        color='cyan', 
        markersize=2, 
        transform=self.map_projection
    )

    # plot ground track
    if self.ground_track is not None:

        # Split ground track in multiple paths when we go off the map
        diffs = np.abs(np.diff(self.ground_track[:, 1])) # differnce in lon between steps
        jump_indices = np.where(diffs > 180)[0]
        
        # Split the array at these indices
        ground_tracks = []
        start_idx = 0
        
        for idx in jump_indices:
            ground_tracks.append(self.ground_track[start_idx:idx+1])
            start_idx = idx + 1
        
        # Add the last segment
        if start_idx < len(self.ground_track):
            ground_tracks.append(self.ground_track[start_idx:])

        # make sure the path touches the edge of the map
        for i, path in enumerate(ground_tracks):
            # work on a copy so we don't modify the original segments
            path_mod = path.copy()

            # prepend the last point of the previous segment adjusted by +/-360
            if i > 0:
                prev_last = ground_tracks[i-1][-1]
                prev_lon = prev_last[1]
                curr_first_lon = path[0, 1]
                if abs(prev_lon - curr_first_lon) > 180:
                    if prev_lon > curr_first_lon:
                        adj_prev_lon = prev_lon - 360
                    else:
                        adj_prev_lon = prev_lon + 360
                    prev_point = np.array([[prev_last[0], adj_prev_lon]])
                    path_mod = np.vstack([prev_point, path_mod])

            # append the first point of the next segment adjusted by +/-360
            if i < len(ground_tracks) - 1:
                next_first = ground_tracks[i+1][0]
                next_lon = next_first[1]
                curr_last_lon = path[-1, 1]
                if abs(curr_last_lon - next_lon) > 180:
                    if next_lon > curr_last_lon:
                        adj_next_lon = next_lon - 360
                    else:
                        adj_next_lon = next_lon + 360
                    next_point = np.array([[next_first[0], adj_next_lon]])
                    path_mod = np.vstack([path_mod, next_point])

            self.map_ax.plot(
                path_mod[:, 1],
                path_mod[:, 0],
                transform=self.map_projection,
                color='orange'
            )
            
    # plot subpoint 
    if latitude is not None and longitude is not None:
        self.map_ax.plot(
            longitude, 
            latitude, 
            'o', 
            color='red', 
            markersize=2, 
            transform=self.map_projection
        )

    # plot circle
    if altitude is not None:
        earth_radius = 6378 # km

        theta = np.arccos(earth_radius/(altitude + earth_radius))
        radius = earth_radius * theta

        plot_geodesic_circle(self.map_ax, longitude, latitude, radius, color='red', linewidth=1)

    # Grid
    gl = self.map_ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels = False
    gl.right_labels = False
            
    # minimize margins to maximize map area
    self.map_figure.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)

    self.map_figure.tight_layout()
    self.map_canvas.draw()

def plot_geodesic_circle(ax, lon, lat, radius_km, **kwargs):
    '''
    Parameters:
        ax (axis): Axis of figure
        lon (float): longnitude of circle center
        lat (float): latitude of circle center
        radius_km (float): radius of circle
        **kwargs (any): arguments regarding the style like color, linewidth, etc...
    '''
    # Create a geodesic circle
    geod = geodesic.Geodesic()
    circle_points = geod.circle(lon, lat, radius_km * 1000, n_samples=100)
        
    # Extract coordinates
    circle_lons = circle_points[:, 0]
    circle_lats = circle_points[:, 1]

    # Plot the circle
    ax.plot(circle_lons, circle_lats, transform=ccrs.Geodetic(), **kwargs)
    
    # close the circle
    start_point = circle_points[0]
    end_point = circle_points[-1]
    if abs(start_point[0] - end_point[0]) > 180: # if it goes over the 180° meridian plot in 2 parts
        lons = [start_point[0], 180]
        lats = [start_point[1], start_point[1]]
        ax.plot(lons, lats, transform=ccrs.Geodetic(), **kwargs)

        lons = [-180, end_point[0]]
        lats = [end_point[1], end_point[1]]
        ax.plot(lons, lats, transform=ccrs.Geodetic(), **kwargs)
    else:
        lons = [start_point[0], end_point[0]]
        lats = [start_point[1], end_point[1]]
        ax.plot(lons, lats, transform=ccrs.Geodetic(), **kwargs)

    # Create a polygon for filling
    fill_color = kwargs.get('color', 'red')
    fill_alpha = 0.1

    # Handle the case where the circle crosses the dateline
    if abs(start_point[0] - end_point[0]) > 180:
        try:
            # Split the circle into two parts at the dateline
            split_idx = np.where(np.abs(np.diff(circle_lons)) > 180)[0][0]
            
            # First part (before the dateline)
            poly1_lons = circle_lons[:split_idx+1]
            poly1_lats = circle_lats[:split_idx+1]
            
            # Second part (after the dateline)
            poly2_lons = circle_lons[split_idx+1:]
            poly2_lats = circle_lats[split_idx+1:]
            
            # Create and add the first polygon
            poly1_xy = np.column_stack([poly1_lons, poly1_lats])
            poly1 = Polygon(poly1_xy, closed=True, facecolor=fill_color, alpha=fill_alpha, 
                        transform=ccrs.Geodetic(), **{k:v for k,v in kwargs.items() if k not in ['color', 'linestyle', 'linewidth']})
            ax.add_patch(poly1)
            
            # Create and add the second polygon
            poly2_xy = np.column_stack([poly2_lons, poly2_lats])
            poly2 = Polygon(poly2_xy, closed=True, facecolor=fill_color, alpha=fill_alpha,
                        transform=ccrs.Geodetic(), **{k:v for k,v in kwargs.items() if k not in ['color', 'linestyle', 'linewidth']})
            ax.add_patch(poly2)
        except:
            '''
            There is edge case when the satellite is close to a pole. 
            
                split_idx = np.where(np.abs(np.diff(circle_lons)) > 180)[0][0]
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^
            IndexError: index 0 is out of bounds for axis 0 with size 0
            
            It only concerns the drawing of the polygon. 
            There is not visible mistake or artefact on the map, therefore we can catch the error here and ignore it.
            '''
            pass  
    else:
        # Create a simple polygon if the circle doesn't cross the dateline
        poly_xy = np.column_stack([circle_lons, circle_lats])
        poly = Polygon(poly_xy, closed=True, facecolor=fill_color, alpha=fill_alpha,
                    transform=ccrs.Geodetic(), **{k:v for k,v in kwargs.items() if k not in ['color', 'linestyle', 'linewidth']})
        ax.add_patch(poly)

def update_ui(self, data):
    '''
    This function gets called via Signal and Slot by core/main_loop.py
    '''

    az          = data['az']
    el          = data['el']
    slant_range = data['slant_range']
    range_rate  = data['range_rate']
    latitude    = data['latitude']
    longitude   = data['longitude']
    altitude    = data['altitude']
    f1          = data['f1']

    # Target Azimuth and Elevation
    if az is not None and el is not None:
        self.target_azimuth.setText(f'{az:.1f}°')
        self.target_elevation.setText(f'{el:.1f}°')
    else:
        self.target_azimuth.setText('N/A')
        self.target_elevation.setText('N/A')
    
    # Doppler Shift
    if f1 is not None:
        self.doppler_shifted_freq.setText(f'{f1:.6f}')
    else:
        self.doppler_shifted_freq.setText('N/A')

    # World Map
    try:
        self.update_map(latitude, longitude, altitude)
    except Exception as e:
        self.log_message(f'Error updating Map: {str(e)}')
        print(traceback.format_exc())

    # Clock
    self.UTC_text.setDateTime(QDateTime.currentDateTimeUtc())

    # Altitude
    if altitude is not None:
        self.altitude_text.setText(f'{altitude:.0f} km')
    else:
        self.altitude_text.setText('N/A')

    # Range
    if slant_range is not None:
        self.range_text.setText(f'{slant_range:.0f} km')
    else:
        self.range_text.setText('N/A')

    # Range Rate
    if range_rate is not None:
        self.range_rate_text.setText(f'{range_rate:.3f} km/s')
    else:
        self.range_rate_text.setText('N/A')

def update_ui_tracking(self, tracking):
    '''
    This function updates the UI when the tracking state changes
    '''
    if tracking:
        self.tracking_btn.setText('Stop Tracking')

        # ensures that the button is checked if the function was not called by the button
        self.tracking_btn.blockSignals(True)
        self.tracking_btn.setChecked(True)
        self.tracking_btn.blockSignals(False)
    else:
        self.tracking_btn.setText('Start Tracking')

        # uncheck "Start Tracking at AOS" to prevent immediate restart of tracking
        self.start_tracking_at_AOS_btn.setChecked(False)

        # ensures that the button is not checked if the function was not called by the button
        self.tracking_btn.blockSignals(True)
        self.tracking_btn.setChecked(False)
        self.tracking_btn.blockSignals(False)    
        