# Datos comunitarios (referencia completa)

Hojas públicas importadas como JSON. **No sustituyen** el catálogo XML del `.pak`; complementan diseño, masas, fricción, colores y sockets.

## Libros importados (35 hojas)

| Libro | Hojas |
|-------|--------|
| [USDS Vlad Vulcan](https://docs.google.com/spreadsheets/d/1_dNNE91snTCbY34YhWtG6mAK-GyCBTx4sIa9Ik9_Kjs/edit) | Trucks, Trucks (RU), Trucks per Region, Tires, Engines, Gearboxes, Cargo, Trailers, Addons, Trucks2 |
| [SR!NFO](https://docs.google.com/spreadsheets/d/1TPla-u2zxpzFMhpxzymhwzxDU_x85Y_1SxylgRPonH0/edit) | Trucks, Engines, Gearboxes, Wheels, Addons, Trailers, Cargo, Color Codes |
| [SnowRunner Extras](https://docs.google.com/spreadsheets/d/13e5VlopEefAsh5N9G1a9HFKpxxORTHPnzJC7CC6Blvw/edit) | Truck List, Addons, Addons 2, Gearboxes, Tires, Trailers & Winches, Cargo, Vehicles To Find, Missions, DLC Trucks, DLC Releases, Addon Color Matching, Gas Tank Volumes, JAT Issue List, Engines (WIP) |

## Archivos

- `{id}.json` — una hoja por archivo (`usds_trucks.json`, `srinfo_engines.json`, …)
- `combined_trucks.json`, `combined_engines.json`, … — agregados por tema
- `fuentes.json` — manifiesto completo
- Aliases: `cargo.json`, `wheels_comunidad.json`, `truck_colors.json`, `addon_colors.json`, `addons_usds.json`

## Comandos

```powershell
python datos/importar_comunidad.py --fetch
python consultar_base.py comunidad
python consultar_base.py buscar tatra
python consultar_base.py cargo cement
python consultar_base.py wheel "OHD I"
```

CSV crudos: `datos/raw/comunidad/*.csv`
