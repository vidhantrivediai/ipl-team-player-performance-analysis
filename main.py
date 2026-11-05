
import zipfile
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE SETTINGS ----------------

st.set_page_config(
    page_title="IPL Performance Analysis",
    page_icon="🏏",
    layout="wide"
)

st.title("🏏 IPL Team and Player Performance Analysis")
st.caption("Interactive IPL analytics dashboard")

# ---------------- HELPER FUNCTIONS ----------------

def find_col(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None


def number_col(df, col):
    if col and col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0)

    return pd.Series(0, index=df.index, dtype="float64")


# ---------------- LOAD DATASETS ----------------

st.sidebar.header("IPL Dataset")

try:
    matches = pd.read_csv("matches.csv")

    with zipfile.ZipFile("deliveries.zip", "r") as zip_file:

        # Find a file inside ZIP, regardless of its spelling
        files_inside_zip = [
            name for name in zip_file.namelist()
            if not name.endswith("/")
        ]

        if not files_inside_zip:
            st.error("The ZIP file is empty.")
            st.stop()

        # Prefer CSV or CSV.TXT files
        csv_files = [
            name for name in files_inside_zip
            if name.lower().endswith((".csv", ".csv.txt"))
        ]

        # If extension is unusual, use the first file
        selected_file = (
            csv_files[0] if csv_files else files_inside_zip[0]
        )

        with zip_file.open(selected_file) as file:
            df = pd.read_csv(file)

    st.sidebar.success("Datasets loaded successfully!")

except FileNotFoundError as e:
    st.error(f"Dataset file not found: {e}")
    st.info("Check that matches.csv and deliveries.zip are in your GitHub repository.")
    st.stop()

except zipfile.BadZipFile:
    st.error("deliveries.zip is not a valid ZIP file.")
    st.stop()

except Exception as e:
    st.error(f"Dataset loading error: {e}")
    st.stop()


# ---------------- IDENTIFY COLUMNS ----------------

season_col = find_col(matches, ["season", "Season", "year"])
winner_col = find_col(matches, ["winner", "Winner"])
team1_col = find_col(matches, ["team1", "Team1"])
team2_col = find_col(matches, ["team2", "Team2"])

match_id_col = find_col(matches, ["id", "match_id"])
delivery_id_col = find_col(df, ["match_id", "id"])

batter_col = find_col(df, ["batter", "batsman"])
bowler_col = find_col(df, ["bowler"])

runs_col = find_col(df, ["batter_runs", "batsman_runs"])
total_runs_col = find_col(df, ["total_runs"])

wide_col = find_col(df, ["wide_runs"])
noball_col = find_col(df, ["noball_runs"])
bye_col = find_col(df, ["bye_runs"])
legbye_col = find_col(df, ["legbye_runs"])
penalty_col = find_col(df, ["penalty_runs"])

dismissal_col = find_col(df, ["dismissal_kind"])
player_out_col = find_col(df, ["player_dismissed"])


# ---------------- DATASET OVERVIEW ----------------

st.header("📊 Dataset Overview")

c1, c2, c3 = st.columns(3)

c1.metric("Total Matches", f"{len(matches):,}")
c2.metric("Total Deliveries", f"{len(df):,}")

if batter_col:
    c3.metric("Total Batters", f"{df[batter_col].nunique():,}")
else:
    c3.metric("Total Batters", "N/A")


# ---------------- SEASON FILTER ----------------

selected_matches = matches.copy()
df_view = df.copy()

if season_col:

    seasons = sorted(
        matches[season_col].dropna().unique().tolist(),
        key=lambda x: str(x)
    )

    selected_season = st.sidebar.selectbox(
        "Select IPL Season",
        ["All Seasons"] + seasons
    )

    if selected_season != "All Seasons":

        selected_matches = matches[
            matches[season_col] == selected_season
        ].copy()

        if match_id_col and delivery_id_col:

            selected_ids = selected_matches[match_id_col].unique()

            df_view = df[
                df[delivery_id_col].isin(selected_ids)
            ].copy()

        else:
            st.warning(
                "Match ID column not found. "
                "Season filter is applied only to matches."
            )


# ---------------- TEAM PERFORMANCE ----------------

st.header("🏆 Team Performance Analysis")

if winner_col and team1_col and team2_col:

    played = pd.concat([
        selected_matches[team1_col],
        selected_matches[team2_col]
    ]).dropna().value_counts()

    wins = selected_matches[winner_col].dropna().value_counts()

    team_stats = pd.DataFrame({
        "Team": played.index,
        "Matches Played": played.values
    })

    team_stats["Wins"] = (
        team_stats["Team"].map(wins).fillna(0).astype(int)
    )

    team_stats["Win Percentage"] = (
        team_stats["Wins"] /
        team_stats["Matches Played"] * 100
    ).round(2)

    team_stats = team_stats.sort_values(
        "Wins", ascending=False
    )

    st.subheader("Team Statistics")

    st.dataframe(
        team_stats,
        use_container_width=True,
        hide_index=True
    )

    fig = px.bar(
        team_stats,
        x="Team",
        y="Wins",
        color="Team",
        title="Total Wins by IPL Team"
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        team_stats,
        x="Team",
        y="Win Percentage",
        color="Team",
        title="Team Win Percentage"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Team or winner columns were not found.")


# ---------------- SEASON ANALYSIS ----------------

st.header("📅 Season-wise Analysis")

if season_col:

    season_data = (
        selected_matches.groupby(season_col)
        .size()
        .reset_index(name="Matches")
    )

    season_data[season_col] = season_data[season_col].astype(str)

    fig = px.line(
        season_data,
        x=season_col,
        y="Matches",
        markers=True,
        title="Matches Played by Season"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Season column is not available.")


# ---------------- BATTING PERFORMANCE ----------------

st.header("🏏 Batting Performance")

if batter_col and runs_col:

    batting_data = df_view.copy()

    batting_data["__runs"] = number_col(
        batting_data, runs_col
    )

    batting_data["__wide"] = number_col(
        batting_data, wide_col
    )

    # Wides are not counted as balls faced
    batting_data["__balls_faced"] = (
        batting_data["__wide"] == 0
    ).astype(int)

    batting = batting_data.groupby(batter_col).agg(
        Runs=("__runs", "sum"),
        Balls_Faced=("__balls_faced", "sum")
    ).reset_index()

    batting["Strike Rate"] = (
        batting["Runs"] /
        batting["Balls_Faced"].replace(0, pd.NA) * 100
    ).fillna(0).round(2)

    batting = batting.sort_values(
        "Runs", ascending=False
    )

    st.subheader("Top 10 Batsmen")

    st.dataframe(
        batting.head(10),
        use_container_width=True,
        hide_index=True
    )

    fig = px.bar(
        batting.head(10),
        x=batter_col,
        y="Runs",
        color="Runs",
        title="Top 10 Batsmen by Runs"
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        batting.sort_values(
            "Strike Rate", ascending=False
        ).head(10),
        x=batter_col,
        y="Strike Rate",
        color="Strike Rate",
        title="Top 10 Batsmen by Strike Rate"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Batter or batter-runs column not found.")


# ---------------- BOWLING PERFORMANCE ----------------

st.header("🎯 Bowling Performance")

if bowler_col and total_runs_col:

    bowling_data = df_view.copy()

    bowling_data["__total"] = number_col(
        bowling_data, total_runs_col
    )

    bowling_data["__bye"] = number_col(
        bowling_data, bye_col
    )

    bowling_data["__legbye"] = number_col(
        bowling_data, legbye_col
    )

    bowling_data["__penalty"] = number_col(
        bowling_data, penalty_col
    )

    bowling_data["__wide"] = number_col(
        bowling_data, wide_col
    )

    bowling_data["__noball"] = number_col(
        bowling_data, noball_col
    )

    # Runs charged to bowler
    bowling_data["__conceded"] = (
        bowling_data["__total"]
        - bowling_data["__bye"]
        - bowling_data["__legbye"]
        - bowling_data["__penalty"]
    )

    # Legal deliveries
    bowling_data["__legal_ball"] = (
        (bowling_data["__wide"] == 0) &
        (bowling_data["__noball"] == 0)
    ).astype(int)

    bowling = bowling_data.groupby(bowler_col).agg(
        Runs_Conceded=("__conceded", "sum"),
        Legal_Balls=("__legal_ball", "sum")
    ).reset_index()

    # Calculate wickets
    if dismissal_col:

        excluded = [
            "run out",
            "retired hurt",
            "retired out",
            "obstructing the field"
        ]

        wickets_df = bowling_data[
            bowling_data[dismissal_col].notna() &
            (~bowling_data[dismissal_col]
             .astype(str).str.lower().isin(excluded))
        ]

        wickets = wickets_df[bowler_col].value_counts()

    elif player_out_col:

        wickets = bowling_data[
            bowling_data[player_out_col].notna()
        ][bowler_col].value_counts()

    else:
        wickets = pd.Series(dtype="int64")

    bowling["Wickets"] = (
        bowling[bowler_col].map(wickets).fillna(0).astype(int)
    )

    bowling["Overs"] = (
        bowling["Legal_Balls"] / 6
    ).round(1)

    bowling["Economy"] = (
        bowling["Runs_Conceded"] /
        (bowling["Legal_Balls"] / 6).replace(0, pd.NA)
    ).fillna(0).round(2)

    bowling = bowling.sort_values(
        ["Wickets", "Economy"],
        ascending=[False, True]
    )

    st.subheader("Top 10 Bowlers")

    st.dataframe(
        bowling.head(10),
        use_container_width=True,
        hide_index=True
    )

    fig = px.bar(
        bowling.head(10),
        x=bowler_col,
        y="Wickets",
        color="Wickets",
        title="Top 10 Bowlers by Wickets"
    )

    st.plotly_chart(fig, use_container_width=True)

    economy_data = bowling[
        bowling["Legal_Balls"] >= 60
    ].sort_values("Economy").head(10)

    fig = px.bar(
        economy_data,
        x=bowler_col,
        y="Economy",
        color="Economy",
        title="Best Economy Rates (Minimum 10 Overs)"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Bowler or total-runs column not found.")


# ---------------- DATASET PREVIEW ----------------

st.header("📁 Dataset Preview")

with st.expander("View Matches Dataset"):

    st.dataframe(
        selected_matches.head(20),
        use_container_width=True
    )

with st.expander("View Deliveries Dataset"):

    st.dataframe(
        df_view.head(20),
        use_container_width=True
    )


# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "IPL Team and Player Performance Analysis | BCA AI Project"
)
