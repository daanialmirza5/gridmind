"""Builds the static digital-twin hierarchy: org -> buildings -> floors -> zones -> assets -> meters."""

from dataclasses import dataclass, field

ZONE_TYPES_BY_FLOOR_KIND = {
    "office": ["office", "office", "common_area"],
    "mixed": ["office", "server_room", "common_area"],
    "retail": ["retail_floor", "retail_floor", "common_area"],
}


@dataclass
class AssetSpec:
    id: str
    zone_id: str
    name: str
    asset_type: str
    rated_power_kw: float
    install_year: int


@dataclass
class ZoneSpec:
    id: str
    floor_id: str
    name: str
    zone_type: str
    area_sqm: float
    max_occupancy: int
    assets: list[AssetSpec] = field(default_factory=list)


@dataclass
class FloorSpec:
    id: str
    building_id: str
    name: str
    level: int
    zones: list[ZoneSpec] = field(default_factory=list)


@dataclass
class MeterSpec:
    id: str
    building_id: str
    zone_id: str | None
    asset_id: str | None
    meter_type: str
    unit: str = "kWh"


@dataclass
class BuildingSpec:
    id: str
    organization_id: str
    name: str
    address: str
    area_sqm: float
    kind: str  # office, mixed, retail -- drives asset/zone mix
    floors: list[FloorSpec] = field(default_factory=list)
    meters: list[MeterSpec] = field(default_factory=list)


BUILDING_DEFS = [
    {"id": "bld-hq", "name": "Harborview Headquarters", "kind": "office", "floors": 4, "zones_per_floor": 2},
    {"id": "bld-dc", "name": "Meridian Tech Campus", "kind": "mixed", "floors": 3, "zones_per_floor": 2},
    {"id": "bld-rt", "name": "Cascade Retail Center", "kind": "retail", "floors": 3, "zones_per_floor": 2},
]


def build_structure(org_id: str = "org-gridmind-demo") -> list[BuildingSpec]:
    buildings: list[BuildingSpec] = []
    asset_counter = 0
    meter_counter = 0

    for bdef in BUILDING_DEFS:
        building = BuildingSpec(
            id=bdef["id"],
            organization_id=org_id,
            name=bdef["name"],
            address=f"{bdef['name']} Site, Demo City",
            area_sqm=0.0,
            kind=bdef["kind"],
        )
        zone_kinds = ZONE_TYPES_BY_FLOOR_KIND[bdef["kind"]]

        # Building main meter
        meter_counter += 1
        building.meters.append(
            MeterSpec(
                id=f"MTR-{meter_counter:04d}",
                building_id=building.id,
                zone_id=None,
                asset_id=None,
                meter_type="main",
            )
        )

        total_area = 0.0
        for level in range(1, bdef["floors"] + 1):
            floor = FloorSpec(
                id=f"{building.id}-fl-{level}",
                building_id=building.id,
                name=f"Floor {level}",
                level=level,
            )
            for zi in range(bdef["zones_per_floor"]):
                zone_type = zone_kinds[zi % len(zone_kinds)]
                area = 420.0 if zone_type != "server_room" else 180.0
                total_area += area
                max_occ = 4 if zone_type == "server_room" else (35 if zone_type != "retail_floor" else 60)
                zone = ZoneSpec(
                    id=f"{floor.id}-z{zi + 1}",
                    floor_id=floor.id,
                    name=f"Floor {level} / {'East' if zi % 2 == 0 else 'West'} Wing",
                    zone_type=zone_type,
                    area_sqm=area,
                    max_occupancy=max_occ,
                )

                # HVAC asset (every zone)
                asset_counter += 1
                hvac_power = 45.0 if zone_type == "server_room" else 18.0
                zone.assets.append(
                    AssetSpec(
                        id=f"HVAC-{asset_counter:03d}",
                        zone_id=zone.id,
                        name=f"HVAC-{asset_counter:03d}",
                        asset_type="hvac",
                        rated_power_kw=hvac_power,
                        install_year=2017 + (asset_counter % 6),
                    )
                )

                # Lighting asset (every zone except server rooms, which run dark)
                if zone_type != "server_room":
                    asset_counter += 1
                    zone.assets.append(
                        AssetSpec(
                            id=f"LIGHT-{asset_counter:03d}",
                            zone_id=zone.id,
                            name=f"LIGHT-{asset_counter:03d}",
                            asset_type="lighting",
                            rated_power_kw=4.5,
                            install_year=2019 + (asset_counter % 4),
                        )
                    )

                # Equipment asset for server rooms / retail floors (always-on or heavy load)
                if zone_type in ("server_room", "retail_floor"):
                    asset_counter += 1
                    eq_power = 32.0 if zone_type == "server_room" else 9.0
                    zone.assets.append(
                        AssetSpec(
                            id=f"EQUIP-{asset_counter:03d}",
                            zone_id=zone.id,
                            name=f"EQUIP-{asset_counter:03d}",
                            asset_type="equipment",
                            rated_power_kw=eq_power,
                            install_year=2020,
                        )
                    )

                # Zone submeter
                meter_counter += 1
                building.meters.append(
                    MeterSpec(
                        id=f"MTR-{meter_counter:04d}",
                        building_id=building.id,
                        zone_id=zone.id,
                        asset_id=zone.assets[0].id,  # primary asset attribution (HVAC)
                        meter_type="submeter",
                    )
                )

                floor.zones.append(zone)
            building.floors.append(floor)

        building.area_sqm = total_area
        buildings.append(building)

    return buildings
