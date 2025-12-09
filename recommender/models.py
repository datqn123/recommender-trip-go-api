# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Accounts(models.Model):
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'accounts'


class AccountsRoles(models.Model):
    pk = models.CompositePrimaryKey('account_id', 'role_id')
    account = models.ForeignKey(Accounts, models.DO_NOTHING)
    role = models.ForeignKey('Roles', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'accounts_roles'


class Airlines(models.Model):
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'airlines'


class Airports(models.Model):
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    location = models.ForeignKey('Locations', models.DO_NOTHING, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'airports'


class Amenities(models.Model):
    id = models.BigAutoField(primary_key=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(unique=True, max_length=255)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    is_prominent = models.TextField(blank=True, null=True)  # This field type is a guess.
    category = models.ForeignKey('AmenityCategories', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'amenities'


class AmenityCategories(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'amenity_categories'


class BookingPassengers(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=255, blank=True, null=True)
    id_number = models.CharField(max_length=255, blank=True, null=True)
    nationality = models.CharField(max_length=255, blank=True, null=True)
    passenger_type = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    booking = models.ForeignKey('Bookings', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'booking_passengers'


class Bookings(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    booking_code = models.CharField(unique=True, max_length=255)
    check_in_date = models.DateTimeField(blank=True, null=True)
    check_out_date = models.DateTimeField(blank=True, null=True)
    contact_email = models.CharField(max_length=255, blank=True, null=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=255, blank=True, null=True)
    discount_amount = models.FloatField(blank=True, null=True)
    final_price = models.FloatField(blank=True, null=True)
    is_paid = models.TextField(blank=True, null=True)  # This field type is a guess.
    payment_method = models.CharField(max_length=11, blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=9, blank=True, null=True)
    total_price = models.FloatField(blank=True, null=True)
    type = models.CharField(max_length=6, blank=True, null=True)
    flight = models.ForeignKey('Flights', models.DO_NOTHING, blank=True, null=True)
    flight_seat = models.ForeignKey('FlightSeats', models.DO_NOTHING, blank=True, null=True)
    room = models.ForeignKey('Rooms', models.DO_NOTHING, blank=True, null=True)
    tour = models.ForeignKey('Tours', models.DO_NOTHING, blank=True, null=True)
    tour_schedule = models.ForeignKey('TourSchedules', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(Accounts, models.DO_NOTHING, blank=True, null=True)
    voucher = models.ForeignKey('Vouchers', models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bookings'


class FavoriteHotels(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    account = models.ForeignKey(Accounts, models.DO_NOTHING)
    hotel = models.ForeignKey('Hotels', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'favorite_hotels'
        unique_together = (('account', 'hotel'),)


class FlightSeats(models.Model):
    available_quantity = models.IntegerField(blank=True, null=True)
    has_meal = models.TextField(blank=True, null=True)  # This field type is a guess.
    is_changeable = models.TextField(blank=True, null=True)  # This field type is a guess.
    is_refundable = models.TextField(blank=True, null=True)  # This field type is a guess.
    price = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    flight = models.ForeignKey('Flights', models.DO_NOTHING, blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    cabin_baggage = models.CharField(max_length=255, blank=True, null=True)
    checked_baggage = models.CharField(max_length=255, blank=True, null=True)
    seat_class = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'flight_seats'


class Flights(models.Model):
    airline = models.ForeignKey(Airlines, models.DO_NOTHING, blank=True, null=True)
    arrival_airport = models.ForeignKey(Airports, models.DO_NOTHING, blank=True, null=True)
    arrival_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    departure_airport = models.ForeignKey(Airports, models.DO_NOTHING, related_name='flights_departure_airport_set', blank=True, null=True)
    departure_time = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    duration = models.CharField(max_length=255, blank=True, null=True)
    flight_number = models.CharField(max_length=255, blank=True, null=True)
    image = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'flights'


class HotelImages(models.Model):
    hotel = models.ForeignKey('Hotels', models.DO_NOTHING, blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    caption = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'hotel_images'


class HotelReviews(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    average_rating = models.FloatField(blank=True, null=True)
    cleanliness_rating = models.FloatField(blank=True, null=True)
    comfort_rating = models.FloatField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    facilities_rating = models.FloatField(blank=True, null=True)
    location_rating = models.FloatField(blank=True, null=True)
    staff_rating = models.FloatField(blank=True, null=True)
    hotel = models.ForeignKey('Hotels', models.DO_NOTHING)
    user = models.ForeignKey(Accounts, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'hotel_reviews'


class HotelViews(models.Model):
    pk = models.CompositePrimaryKey('hotel_id', 'view_type')
    hotel = models.ForeignKey('Hotels', models.DO_NOTHING)
    view_type = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'hotel_views'


class Hotels(models.Model):
    average_rating = models.FloatField(blank=True, null=True)
    cleanliness_score = models.FloatField(blank=True, null=True)
    comfort_score = models.FloatField(blank=True, null=True)
    facilities_score = models.FloatField(blank=True, null=True)
    location_score = models.FloatField(blank=True, null=True)
    price_per_night_from = models.FloatField(blank=True, null=True)
    staff_score = models.FloatField(blank=True, null=True)
    star_rating = models.IntegerField(blank=True, null=True)
    total_reviews = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    location = models.ForeignKey('Locations', models.DO_NOTHING)
    updated_at = models.DateTimeField(blank=True, null=True)
    address = models.CharField(max_length=255)
    check_in_time = models.CharField(max_length=255, blank=True, null=True)
    check_out_time = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.CharField(max_length=255, blank=True, null=True)
    contact_phone = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=255)
    design_style = models.CharField(max_length=12, blank=True, null=True)
    price_range = models.CharField(max_length=8, blank=True, null=True)
    type = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'hotels'


class HotelsAmenities(models.Model):
    pk = models.CompositePrimaryKey('amenity_id', 'hotel_id')
    amenity = models.ForeignKey(Amenities, models.DO_NOTHING)
    hotel = models.ForeignKey(Hotels, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'hotels_amenities'


class InvalidatedTokens(models.Model):
    expiry_time = models.DateTimeField(blank=True, null=True)
    id = models.CharField(primary_key=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'invalidated_tokens'


class Locations(models.Model):
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    name = models.CharField(unique=True, max_length=255)
    slug = models.CharField(unique=True, max_length=255)
    thumbnail = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'locations'


class Permissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'permissions'


class RefreshTokens(models.Model):
    account = models.OneToOneField(Accounts, models.DO_NOTHING, blank=True, null=True)
    expiry_date = models.DateTimeField()
    id = models.BigAutoField(primary_key=True)
    token = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'refresh_tokens'


class Roles(models.Model):
    id = models.BigAutoField(primary_key=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(unique=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'roles'


class RolesPermissions(models.Model):
    pk = models.CompositePrimaryKey('permission_id', 'role_id')
    permission = models.ForeignKey(Permissions, models.DO_NOTHING)
    role = models.ForeignKey(Roles, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'roles_permissions'


class Rooms(models.Model):
    area = models.FloatField(blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)
    is_available = models.TextField(blank=True, null=True)  # This field type is a guess.
    price = models.FloatField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    hotel = models.ForeignKey(Hotels, models.DO_NOTHING)
    id = models.BigAutoField(primary_key=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'rooms'


class SearchHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(blank=True, null=True)
    hotel_type = models.CharField(max_length=9, blank=True, null=True)
    keyword = models.CharField(max_length=255, blank=True, null=True)
    max_price = models.FloatField(blank=True, null=True)
    min_price = models.FloatField(blank=True, null=True)
    result_count = models.IntegerField(blank=True, null=True)
    search_type = models.CharField(max_length=8, blank=True, null=True)
    star_rating = models.IntegerField(blank=True, null=True)
    account = models.ForeignKey(Accounts, models.DO_NOTHING)
    location = models.ForeignKey(Locations, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'search_history'


class TourImages(models.Model):
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    tour = models.ForeignKey('Tours', models.DO_NOTHING, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    image_url = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'tour_images'


class TourItineraries(models.Model):
    day_number = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    tour = models.ForeignKey('Tours', models.DO_NOTHING, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tour_itineraries'


class TourSchedules(models.Model):
    available_seats = models.IntegerField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    start_date = models.DateField()
    created_at = models.DateTimeField(blank=True, null=True)
    id = models.BigAutoField(primary_key=True)
    tour = models.ForeignKey('Tours', models.DO_NOTHING, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tour_schedules'


class Tours(models.Model):
    price = models.FloatField(blank=True, null=True)
    price_adult = models.FloatField(blank=True, null=True)
    price_child = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    destination = models.ForeignKey(Locations, models.DO_NOTHING)
    id = models.BigAutoField(primary_key=True)
    start_location = models.ForeignKey(Locations, models.DO_NOTHING, related_name='tours_start_location_set')
    updated_at = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    duration = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255)
    thumbnail = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255)
    transportation = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tours'


class UserProfiles(models.Model):
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    user = models.OneToOneField(Accounts, models.DO_NOTHING, primary_key=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, null=True)
    full_name = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    avatar_url = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_profiles'


class VoucherAppliedFlights(models.Model):
    pk = models.CompositePrimaryKey('voucher_id', 'flight_id')
    voucher = models.ForeignKey('Vouchers', models.DO_NOTHING)
    flight = models.ForeignKey(Flights, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'voucher_applied_flights'


class VoucherAppliedHotels(models.Model):
    pk = models.CompositePrimaryKey('hotel_id', 'voucher_id')
    hotel = models.ForeignKey(Hotels, models.DO_NOTHING)
    voucher = models.ForeignKey('Vouchers', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'voucher_applied_hotels'


class VoucherAppliedLocations(models.Model):
    pk = models.CompositePrimaryKey('voucher_id', 'location_id')
    voucher = models.ForeignKey('Vouchers', models.DO_NOTHING)
    location = models.ForeignKey(Locations, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'voucher_applied_locations'


class VoucherAppliedTours(models.Model):
    pk = models.CompositePrimaryKey('tour_id', 'voucher_id')
    tour = models.ForeignKey(Tours, models.DO_NOTHING)
    voucher = models.ForeignKey('Vouchers', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'voucher_applied_tours'


class Vouchers(models.Model):
    discount_value = models.FloatField(blank=True, null=True)
    is_active = models.TextField(blank=True, null=True)  # This field type is a guess.
    max_discount_amount = models.FloatField(blank=True, null=True)
    min_order_value = models.FloatField(blank=True, null=True)
    usage_count = models.IntegerField(blank=True, null=True)
    usage_limit = models.IntegerField(blank=True, null=True)
    user_limit = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField()
    id = models.BigAutoField(primary_key=True)
    start_date = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    code = models.CharField(unique=True, max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=12, blank=True, null=True)
    scope = models.CharField(max_length=11, blank=True, null=True)
    for_new_users_only = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'vouchers'
