# Data Requirements Map - Complete Data Points & Best Collection Methods

**Purpose:** Map every data point needed for the rebounding prediction system to the best collection method.

**Approach:** Use pre-existing datasets for historical data, API only for current year updates.

---

## 📊 DATA CATEGORIES & COLLECTION METHODS

### 1. PLAYER STATISTICS (Historical - 5 Years)

**Data Points Needed:**
- Season totals: Games, Minutes, Points, Rebounds (ORB, DRB, TRB)
- Advanced metrics: TRB%, ORB%, DRB%, PER, TS%, USG%
- Per-36 rates: Rebounds per 36 minutes
- Shooting: FG%, 3P%, FT%, FGA, 3PA, FTA
- Other: Assists, Steals, Blocks, Turnovers, Fouls
- Physical: Height, Weight, Position
- Team affiliation: Team ID per season

**Best Collection Method:**
- **Source:** Kaggle NBA Player Stats Dataset
- **Format:** CSV with season totals (already aggregated)
- **Time:** 10 minutes to download
- **Coverage:** 2019-20 through 2023-24 seasons
- **Why:** Pre-aggregated, reliable, no API calls needed

**Alternative (if Kaggle unavailable):**
- Basketball Reference bulk CSV export
- NBA.com stats page scraping (last resort)

---

### 2. TEAM STATISTICS (Historical - 5 Years)

**Data Points Needed:**
- Season totals: Wins, Losses, Games Played
- Rebounding: Team TRB, ORB, DRB, TRB%, ORB%, DRB%
- Pace: Possessions per game, Pace rating
- Shooting: Team FG%, 3P%, FT%, FGA, 3PA
- Defense: Opponent FG%, Opponent 3P%, Defensive Rating
- Rebounding philosophy: Offensive/defensive rebounding rates

**Best Collection Method:**
- **Source:** Kaggle NBA Team Stats Dataset
- **Format:** CSV with season totals
- **Time:** 10 minutes to download
- **Coverage:** 2019-20 through 2023-24 seasons
- **Why:** Pre-aggregated, includes all team metrics

**Alternative:**
- Basketball Reference team stats export
- Aggregate from player stats (if needed)

---

### 3. CURRENT YEAR PLAYER STATS (2024-25)

**Data Points Needed:**
- Same as historical (but current season)
- Updated daily for predictions

**Best Collection Method:**
- **Source:** NBA Stats API
- **Endpoint:** `/playerdashboardbygeneralsplits`
- **Frequency:** Daily updates (7 AM, 3 PM MT)
- **Why:** Need current data, API is fine for daily updates
- **Time:** ~5-10 minutes per update

---

### 4. CURRENT YEAR TEAM STATS (2024-25)

**Data Points Needed:**
- Same as historical (but current season)
- Updated daily

**Best Collection Method:**
- **Source:** NBA Stats API
- **Endpoint:** `/teamdashboardbygeneralsplits`
- **Frequency:** Daily updates
- **Time:** ~2-3 minutes per update

---

### 5. SPATIAL DATA (Rebound Zones)

**Data Points Needed:**
- Zone-based rebound collection: Paint, Mid-Range, 3PT, Perimeter
- Player zone preferences: Where each player collects rebounds
- League-wide zone distribution: Where rebounds occur most
- Position-based defaults: Typical zones by position

**Best Collection Method:**
- **Source:** NBA Stats API (Shot Chart + Box Score)
- **Endpoints:** 
  - `/shotchartdetail` (for shot locations, infer rebound zones)
  - `/boxscoreadvancedv2` (for zone breakdowns if available)
- **Fallback:** Position-based defaults (if zone data unavailable)
- **Historical:** Use position-based defaults for past seasons
- **Current:** Try to get actual zone data from API

**Why This Works:**
- Spatial data is derived/estimated, not raw tracking data
- Position-based defaults are acceptable for historical
- Current year can use shot chart data to infer zones

---

### 6. LINEUP DATA

**Data Points Needed:**
- Lineup compositions: Who plays together
- Shared minutes: How often players share court
- Lineup rebounding strength: Combined TRB% of lineup
- Positional balance: Number of bigs vs guards on court
- Average lineup height

**Best Collection Method:**
- **Source:** NBA Stats API (Play-by-Play)
- **Endpoint:** `/playbyplayv2` (extract lineups from substitutions)
- **Historical:** Use season averages (who played together most)
- **Current:** Extract from play-by-play data
- **Fallback:** Use roster data + minutes estimates

**Alternative:**
- Basketball Reference lineup data (if available)
- Estimate from player minutes and team rotations

---

### 7. GAME CONTEXT DATA

**Data Points Needed:**
- Rest days: Days since last game
- Back-to-back: Is this a back-to-back game
- Home/Away: Home court advantage
- Travel: Distance traveled, time zone changes
- Playoff vs Regular: Game type
- Game situation: Score differential, clutch situations

**Best Collection Method:**
- **Source:** NBA Stats API + Schedule Data
- **Endpoints:**
  - `/scoreboard` (for game schedule)
  - `/boxscoresummaryv2` (for game context)
- **Historical:** Calculate from game dates and locations
- **Current:** API for schedule and game context
- **Time:** ~5 minutes to calculate for all games

---

### 8. INJURY DATA

**Data Points Needed:**
- Player injury status: Active, Out, Questionable, Probable
- Injury type: Body part, severity
- Expected return: When player will return
- Impact on minutes: How injury affects playing time
- Position impact: If injured player affects rotation

**Best Collection Method:**
- **Source:** Multi-source scraping
- **Sources:**
  - NBA.com injury reports
  - ESPN injury reports
  - Rotowire injury updates
- **Frequency:** Daily updates (7 AM, 3 PM MT)
- **Why:** Most reliable injury data is from news sources
- **Time:** ~10 minutes per update

---

### 9. MATCHUP DATA

**Data Points Needed:**
- Height/Weight advantages: Player vs likely defender
- Head-to-head stats: Historical performance vs opponent
- Positional matchups: Who guards whom
- Team vs Team: Historical team performance

**Best Collection Method:**
- **Source:** Calculated from player/team stats
- **Height/Weight:** From player database (Kaggle)
- **Head-to-head:** Calculate from game logs (if available) or estimate from team matchups
- **Positional:** Estimate from position and rotation data
- **Historical:** Calculate from historical game data
- **Current:** Estimate from current rosters

---

### 10. MOMENTUM & TRENDS

**Data Points Needed:**
- Recent form: Last 5, 10, 15 games averages
- Trend direction: Improving or declining
- Fatigue: Recent workload (minutes in last week)
- Hot/cold streaks: Recent performance vs season average

**Best Collection Method:**
- **Source:** Calculated from game logs
- **Historical:** Use Kaggle game logs (if available) or calculate from season totals
- **Current:** Use API game logs for current season
- **Why:** Derived feature, calculated from base stats

---

### 11. SHOT SELECTION DATA

**Data Points Needed:**
- Team 3-point attempt rate
- Team shot selection profile: Paint, Mid-Range, 3PT percentages
- Expected missed shots: Based on FG% and volume
- Free throw rate
- Turnover rate

**Best Collection Method:**
- **Source:** Calculated from team stats
- **Historical:** From Kaggle team stats
- **Current:** From API team stats
- **Why:** Derived from base shooting stats

---

### 12. FOUL TROUBLE DATA

**Data Points Needed:**
- Player foul rate: Average fouls per game
- Foul rate per 36 minutes
- Opponent foul drawing ability
- Expected game situation: Blowout vs close

**Best Collection Method:**
- **Source:** Calculated from player stats
- **Historical:** From Kaggle player stats
- **Current:** From API player stats
- **Why:** Derived from base stats

---

## 🎯 COLLECTION STRATEGY SUMMARY

### Historical Data (2019-2024) - Use Pre-existing Datasets

| Data Type | Source | Method | Time |
|-----------|--------|--------|------|
| Player Stats | Kaggle | CSV Download | 10 min |
| Team Stats | Kaggle | CSV Download | 10 min |
| Spatial Data | Calculated | Position defaults | 5 min |
| Lineup Data | Calculated | Season averages | 10 min |
| Game Context | Calculated | From schedule | 5 min |
| Matchup Data | Calculated | From stats | 5 min |
| **TOTAL** | | | **~45 minutes** |

### Current Year Data (2024-25) - Use API

| Data Type | Source | Method | Frequency | Time |
|-----------|--------|--------|-----------|------|
| Player Stats | NBA API | `/playerdashboardbygeneralsplits` | Daily | 5-10 min |
| Team Stats | NBA API | `/teamdashboardbygeneralsplits` | Daily | 2-3 min |
| Spatial Data | NBA API | `/shotchartdetail` | Daily | 5 min |
| Lineup Data | NBA API | `/playbyplayv2` | Daily | 5 min |
| Game Context | NBA API | `/scoreboard` | Daily | 2 min |
| Injury Data | Multi-source | Scraping | Daily | 10 min |
| **TOTAL PER UPDATE** | | | | **~30 minutes** |

---

## ✅ IMPLEMENTATION PLAN

### Phase 1: Historical Data Collection (45 minutes)
1. Download Kaggle datasets (20 min)
2. Import to database (20 min)
3. Calculate derived features (5 min)

### Phase 2: Current Year Setup (30 minutes)
1. Set up API collection for current year
2. Test all endpoints
3. Verify data quality

### Phase 3: Daily Updates (30 minutes/day)
1. Run scheduled updates (7 AM, 3 PM MT)
2. Update current year stats
3. Update injury reports
4. Recalculate features

---

## 🔑 KEY POINTS

1. **Historical Data:** Use pre-existing datasets (Kaggle) - fast and reliable
2. **Current Year:** Use API for daily updates - acceptable for small volume
3. **Spatial Data:** Use position-based defaults for historical, API for current
4. **Derived Features:** Calculate from base stats (momentum, trends, etc.)
5. **Keep All Features:** Nothing is lost, just better data collection method

---

**Total Setup Time: ~1.5 hours (vs 15+ hours with current approach)**





