from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="MyApp")
# address is a String e.g. 'Berlin, Germany'
# addressdetails=True does the magic and gives you also the details
location = geolocator.geocode("Bangalore", addressdetails=True)

print(location.latitude)
print(location.longitude)