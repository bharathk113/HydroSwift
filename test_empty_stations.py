import swift_app as swift
stations_wris = swift.wris.stations(variable="sediment",basin='Cauvery')
print("DATAFRAME:")
print(stations_wris)
print("IS EMPTY:", stations_wris.empty)
