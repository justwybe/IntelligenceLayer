"""Tests for FacilityManager — locations, objects, and facility context."""


class TestFacilityLocations:
    def test_add_and_get_location(self, facility):
        lid = facility.add_location("Dining Hall", "common_area", floor=1, description="Main dining")
        loc = facility.get_location(lid)
        assert loc is not None
        assert loc["name"] == "Dining Hall"
        assert loc["location_type"] == "common_area"
        assert loc["floor"] == 1
        assert loc["navigable"] == 1

    def test_find_location_by_name(self, facility):
        facility.add_location("Garden", "outdoor")
        loc = facility.find_location("garden")
        assert loc is not None
        assert loc["name"] == "Garden"

    def test_list_locations(self, facility, sample_facility):
        all_locs = facility.list_locations()
        assert len(all_locs) == 5

    def test_list_locations_by_type(self, facility, sample_facility):
        common = facility.list_locations(location_type="common_area")
        assert len(common) == 2  # Dining Hall + Lobby

    def test_update_location(self, facility):
        lid = facility.add_location("Old Name", "room")
        facility.update_location(lid, name="New Name", floor=3)
        loc = facility.get_location(lid)
        assert loc["name"] == "New Name"
        assert loc["floor"] == 3

    def test_delete_location_clears_objects(self, facility):
        lid = facility.add_location("Room 101", "resident_room")
        oid = facility.add_object("Lamp", location_id=lid)
        facility.delete_location(lid)
        assert facility.get_location(lid) is None
        obj = facility.get_object(oid)
        assert obj is not None
        assert obj["location_id"] is None


class TestFacilityObjects:
    def test_add_and_get_object(self, facility):
        oid = facility.add_object("Reading Glasses", object_type="personal", description="Wire-frame")
        obj = facility.get_object(oid)
        assert obj is not None
        assert obj["name"] == "Reading Glasses"

    def test_find_objects(self, facility):
        facility.add_object("Reading Glasses")
        facility.add_object("Sunglasses")
        facility.add_object("Book")
        results = facility.find_objects("glasses")
        assert len(results) == 2

    def test_list_objects_by_location(self, facility):
        lid = facility.add_location("Room 204", "resident_room")
        facility.add_object("Lamp", location_id=lid)
        facility.add_object("Book", location_id=lid)
        facility.add_object("Remote")  # no location
        objects = facility.list_objects(location_id=lid)
        assert len(objects) == 2

    def test_list_objects_by_owner(self, facility, residents):
        rid = residents.create(name="Martha")
        facility.add_object("Glasses", owner_resident_id=rid)
        facility.add_object("Book", owner_resident_id=rid)
        facility.add_object("TV")
        objects = facility.list_objects(owner_resident_id=rid)
        assert len(objects) == 2

    def test_update_object(self, facility):
        lid = facility.add_location("Room 204", "resident_room")
        oid = facility.add_object("Book")
        facility.update_object(oid, location_id=lid, description="Paperback novel")
        obj = facility.get_object(oid)
        assert obj["location_id"] == lid
        assert obj["description"] == "Paperback novel"

    def test_delete_object(self, facility):
        oid = facility.add_object("Temporary")
        facility.delete_object(oid)
        assert facility.get_object(oid) is None


class TestFacilityContext:
    def test_build_facility_context(self, facility, residents):
        lid = facility.add_location("Dining Hall", "common_area", floor=1, description="Main dining")
        rid = residents.create(name="Martha")
        facility.add_object("Flower Vase", location_id=lid, owner_resident_id=rid)

        ctx = facility.build_facility_context()
        assert "Dining Hall" in ctx
        assert "common_area" in ctx
        assert "Flower Vase" in ctx
        assert "Martha" in ctx

    def test_build_facility_context_empty(self, facility):
        ctx = facility.build_facility_context()
        assert "No facility map configured" in ctx

    def test_non_navigable_shown(self, facility):
        facility.add_location("Kitchen", "staff_area", navigable=False)
        ctx = facility.build_facility_context()
        assert "not navigable" in ctx
