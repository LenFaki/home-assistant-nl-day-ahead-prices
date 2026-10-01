# EnerPrice dashboardvoorbeelden

Deze voorbeelden zijn bedoeld als direct bruikbaar startpunt voor Home Assistant. Vervang de voorbeeld-entiteiten door de entity-ID's uit je eigen installatie. EnerPrice blijft adviserend: de voorbeelden sturen niet zelfstandig een apparaat aan, tenzij je daar bewust zelf een automatisering omheen bouwt.

## 1. Huidige all-in stroomprijs

Gebruik een native Tile-kaart:

```yaml
type: tile
entity: sensor.nl_day_ahead_prices_current_all_in_price
name: Stroomprijs nu
```

Wijkt jouw entity-ID af, kies dan **Huidige All-in Prijs** op de EnerPrice-apparaatpagina.

## 2. Prijsadviseur

```yaml
type: tile
entity: sensor.nl_day_ahead_prices_price_advisor
name: Prijsadvies
```

De Prijsadviseur geeft snel prijsadvies en heeft geen gas-, zonne- of P1-sensor nodig.

## 3. Slim tapwateradvies

De Smart Energy Advisor is een response-actie. Een praktische inrichting gebruikt:
- een werkende EnerPrice-configuratie met actuele all-in prijzen;
- optioneel een gasprijssensor in €/m³;
- bij voorkeur een P1/netvermogenssensor in W;
- optioneel het elektrische vermogen van het flexibele apparaat in W.

Voor netvermogen verwacht EnerPrice **positief = afname** en **negatief = teruglevering**. `unknown` en `unavailable` worden niet als nul behandeld.

Voorbeeld:

```yaml
action: nl_day_ahead_prices.get_smart_energy_advice
data:
  gas_price_entity: sensor.jouw_gasprijs
  grid_power_entity: sensor.jouw_netvermogen
  flexible_load_power_w: 1500
  electric_efficiency: 1.0
  gas_efficiency: 0.90
  gas_kwh_per_m3: 9.769
  solar_surplus_threshold_w: 500
  language: nl
```

Met `flexible_load_power_w` maakt EnerPrice onderscheid tussen volledig en gedeeltelijk overschot. Bij een apparaat van 1500 W is 500 W teruglevering dus 33,3% dekking en niet langer automatisch voldoende om volledig op overschot te draaien. Het resterende netaandeel wordt meegenomen in de effectieve elektrische warmtekosten.

Handige antwoordvelden zijn `state`, `recommendation`, `cheapest_now`, `electric_heat_cost_per_kwh`, `effective_electric_heat_cost_per_kwh`, `gas_heat_cost_per_kwh`, `measured_solar_surplus_w`, `partial_surplus`, `surplus_coverage_percent`, `required_surplus_w`, `next_better_time` en `minutes_until_better`.

## 4. Een EnerPrice-dashboard genereren

Je hoeft een dashboard niet volledig zelf te schrijven. Voer uit:

```yaml
action: nl_day_ahead_prices.generate_dashboard_yaml
data:
  dashboard_type: energy_advisor
  include_market_price: true
  include_all_in_price: true
  include_supplier_info: true
  include_best_periods: true
  include_price_advisor: true
```

Kopieer de teruggegeven YAML naar een Home Assistant-dashboard. Ook `compact` en `full` zijn beschikbaar.

## 5. Veilig automatiseren

Behandel de Smart Energy Advisor als advies en voeg eigen veiligheidsvoorwaarden toe voordat een echt apparaat wordt geschakeld. Behoud bij tapwater altijd de eigen thermostaat, legionella-/hygiënecyclus, maximale temperatuur, minimale draaitijd en beveiligingen van de fabrikant. Een niet-beschikbare sensor mag nooit als toestemming om in te schakelen worden geïnterpreteerd.

## Snelle inrichting

1. Installeer en configureer EnerPrice.
2. Controleer of **Huidige All-in Prijs** een plausibele waarde heeft.
3. Zoek de P1/netvermogenssensor en controleer de tekenrichting.
4. Voeg een gasprijssensor toe als je warmtebronnen wilt vergelijken.
5. Vul het echte elektrische vermogen van het flexibele apparaat in zodra dat bekend is.
6. Test de Smart Energy Advisor handmatig via Ontwikkelaarstools > Acties.
7. Genereer of kopieer een dashboardvoorbeeld.
8. Bouw pas daarna apparaat-automatiseringen met expliciete veiligheidsvoorwaarden.
