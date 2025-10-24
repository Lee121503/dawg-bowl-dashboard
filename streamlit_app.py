import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import combinations

st.set_page_config(page_title="Dawg Bowl Contest Dashboard", layout="wide")

# 🔀 Sidebar mode selector
mode = st.sidebar.selectbox("Choose Mode", ["Dashboard", "Elite Trait Scanner"])

# 🔹 Shared Uploads
st.sidebar.header("📥 Upload Contest Files")
uploaded_weeks = st.sidebar.file_uploader("Upload weekly CSVs", type="csv", accept_multiple_files=True)
uploaded_positions = st.sidebar.file_uploader("Upload Position List Excel", type=["xls", "xlsx"])

# 🔹 Trait Scanner Function
def run_trait_scanner(uploaded_files):
    st.title("🏆 Top 1% Draft Trait Scanner (By Week)")
    if not uploaded_files:
        st.info("📥 Please upload contest CSVs in the Dashboard tab first.")
        return

    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            week_label = file.name.split("_Week_")[1].split("_")[0]
        except Exception as e:
            st.error(f"Error reading {file.name}: {e}")
            continue

        total_entries = len(df)
        top_cutoff = max(1, int(total_entries * 0.01))
        top_df = df.nsmallest(top_cutoff, "place")

        st.subheader(f"📅 Week {week_label}")
        st.markdown(f"**Total Entries:** {total_entries}  \n**Top 1% Cutoff:** Top {top_cutoff} entries")

        all_players = pd.melt(df, id_vars=["place"], value_vars=[f"Player {i}" for i in range(1, 7)], var_name="Slot", value_name="Player")
        top_players = pd.melt(top_df, id_vars=["place"], value_vars=[f"Player {i}" for i in range(1, 7)], var_name="Slot", value_name="Player")

        player_counts = all_players["Player"].value_counts().rename("All Entries")
        top_counts = top_players["Player"].value_counts().rename("Top 1%")

        trait_df = pd.concat([top_counts, player_counts], axis=1).fillna(0)
        trait_df["Elite Hit Rate (%)"] = (trait_df["Top 1%"] / trait_df["All Entries"]) * 100
        trait_df = trait_df.sort_values("Elite Hit Rate (%)", ascending=False)

        st.dataframe(trait_df.style.format({"Elite Hit Rate (%)": "{:.2f}"}))

        # 🔗 Combo Detection
        combo_records = []
        for _, row in top_df.iterrows():
            players = [row[f"Player {i}"] for i in range(1, 7)]
            for pair in combinations(sorted(players), 2):
                combo_records.append(tuple(pair))
        top_combo_counts = pd.Series(combo_records).value_counts().rename("Top 1%")

        combo_records_all = []
        for _, row in df.iterrows():
            players = [row[f"Player {i}"] for i in range(1, 7)]
            for pair in combinations(sorted(players), 2):
                combo_records_all.append(tuple(pair))
        all_combo_counts = pd.Series(combo_records_all).value_counts().rename("All Entries")

        combo_df = pd.concat([top_combo_counts, all_combo_counts], axis=1).fillna(0)
        combo_df["Elite Hit Rate (%)"] = (combo_df["Top 1%"] / combo_df["All Entries"]) * 100
        combo_df = combo_df.reset_index().rename(columns={"index": "Combo"})
        combo_df[["Player A", "Player B"]] = pd.DataFrame(combo_df["Combo"].tolist(), index=combo_df.index)
        combo_df = combo_df[["Player A", "Player B", "Top 1%", "All Entries", "Elite Hit Rate (%)"]]
        combo_df = combo_df.sort_values("Elite Hit Rate (%)", ascending=False)

        st.subheader("🔗 High-Impact Player Combos")
        st.dataframe(combo_df.style.format({"Elite Hit Rate (%)": "{:.2f}"}))

# 🔹 Dashboard Mode
if mode == "Dashboard":
    if uploaded_weeks and uploaded_positions:
        # 🔹 Load and process data
        all_weeks = []
        for file in uploaded_weeks:
            week_label = file.name.split("_Week_")[1].split("_")[0]
            df = pd.read_csv(file)
            df["Week"] = f"Week {week_label}"
            all_weeks.append(df)
        entries_df = pd.concat(all_weeks, ignore_index=True)

        position_df = pd.read_excel(uploaded_positions)
        position_map = dict(zip(position_df["Name"], position_df["Position"]))

        for i in range(1, 7):
            col = f"Player {i}"
            pos_col = f"Pos {i}"
            entries_df[pos_col] = entries_df[col].map(position_map).fillna("Unknown")

        def assign_roles(row):
            roles = {"QB Pick": None, "RB1 Pick": None, "WR1 Pick": None, "WR2 Pick": None, "TE Pick": None, "Flex Pick": None}
            rb_count = wr_count = 0
            used_slots = set()
            for i in range(1, 7):
                pos = row[f"Pos {i}"]
                slot = i
                if pos == "QB" and not roles["QB Pick"]:
                    roles["QB Pick"] = slot; used_slots.add(slot)
                elif pos == "RB" and rb_count < 1:
                    roles["RB1 Pick"] = slot; rb_count += 1; used_slots.add(slot)
                elif pos == "WR" and wr_count < 2:
                    if not roles["WR1 Pick"]: roles["WR1 Pick"] = slot
                    else: roles["WR2 Pick"] = slot
                    wr_count += 1; used_slots.add(slot)
                elif pos == "TE" and not roles["TE Pick"]:
                    roles["TE Pick"] = slot; used_slots.add(slot)
            for i in range(1, 7):
                pos = row[f"Pos {i}"]
                slot = i
                if slot not in used_slots and pos in ["RB", "WR", "TE"]:
                    roles["Flex Pick"] = slot
                    break
            return pd.Series(roles)

        entries_df = pd.concat([entries_df, entries_df.apply(assign_roles, axis=1)], axis=1)
        entries_df["Total Entries"] = entries_df.groupby("username")["username"].transform("count")

        def tag_percentile_tiers(df):
            def tag_group(group):
                total = len(group)
                group["Top_0.1%"] = group["place"].astype(int) <= max(1, round(0.001 * total))
                group["Top_0.5%"] = group["place"].astype(int) <= max(1, round(0.005 * total))
                group["Top_1%"] = group["place"].astype(int) <= max(1, round(0.01 * total))
                return group
            return df.groupby("Week", group_keys=False).apply(tag_group)

        entries_df = tag_percentile_tiers(entries_df)

        # 🔹 Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔥 Heatmap", "🧠 Round 1 Anchor Analysis"])

        # 📊 TAB 1: User-Level Dashboard
        with tab1:
            st.header("📊 User-Level Elite Finish Dashboard")

            selected_week = st.selectbox("Filter by Week", ["All Weeks"] + sorted(entries_df["Week"].unique()))
            filtered_df = entries_df.copy()
            if selected_week != "All Weeks":
                filtered_df = filtered_df[filtered_df["Week"] == selected_week]

            selected_user = st.text_input("Username (optional)")
            min_entries = st.slider("Minimum Entries", 0, int(entries_df["Total Entries"].max()), 0)
            sort_mode = st.radio("Sort by", ["Elite Finish Count", "Elite Finish Rate"])

            user_summary = (
                filtered_df.groupby("username")[["Top_0.1%", "Top_0.5%", "Top_1%"]]
                .sum()
                .astype(int)
                .join(filtered_df["username"].value_counts().rename("Total Entries"))
                .reset_index()
                .rename(columns={"index": "username"})
            )

            user_summary["Top 0.1% Rate"] = user_summary["Top_0.1%"] / user_summary["Total Entries"]
            user_summary["Top 0.5% Rate"] = user_summary["Top_0.5%"] / user_summary["Total Entries"]
            user_summary["Top 1% Rate"] = user_summary["Top_1%"] / user_summary["Total Entries"]

            filtered = user_summary[user_summary["Total Entries"] >= min_entries]
            if selected_user:
                filtered = filtered[filtered["username"].str.lower() == selected_user.lower()]

            sort_cols = ["Top_0.1%", "Top_0.5%", "Top_1%"] if sort_mode == "Elite Finish Count" else ["Top 0.1% Rate", "Top 0.5% Rate", "Top 1% Rate"]
            st.dataframe(
                filtered.sort_values(by=sort_cols, ascending=False)
                .style.format({
                    "Top 0.1% Rate": "{:.2%}",
                    "Top 0.5% Rate": "{:.2%}",
                    "Top 1% Rate": "{:.2%}"
                })
            )

            st.download_button("📤 Export Filtered Table", filtered.to_csv(index=False), "filtered_user_summary.csv")

        # 🔥 TAB 2: Heatmap
        with tab2:
            st.header("🔥 Heatmap: Draft Position Frequency by Round")

            tier_option = st.selectbox("Heatmap Percentile Tier", ["All Entries", "Top 1%", "Top 0.5%", "Top 0.1%"])
            week_option = st.selectbox("Heatmap Week Filter", ["All Weeks"] + sorted(entries_df["Week"].unique()))
            heatmap_user = st.text_input("Heatmap Username Filter (optional)")

            heatmap_df = entries_df.copy()
            if week_option != "All Weeks":
                heatmap_df = heatmap_df[heatmap_df["Week"] == week_option]
            if tier_option == "Top 1%":
                heatmap_df = heatmap_df[heatmap_df["Top_1%"]]
            elif tier_option == "Top 0.5%":
                heatmap_df = heatmap_df[heatmap_df["Top_0.5%"]]
            elif tier_option == "Top 0.1%":
                heatmap_df = heatmap_df[heatmap_df["Top_0.1%"]]
            if heatmap_user:
                heatmap_df = heatmap_df[heatmap_df["username"].str.lower() == heatmap_user.lower()]

            melted = heatmap_df.melt(
                value_vars=[f"Pos {i}" for i in range(1, 7)],
                var_name="Round",
                value_name="Position"
            )
            melted["Round"] = melted["Round"].str.extract(r"(\d)").astype(int)

            heatmap_data = (
                melted.groupby(["Round", "Position"])
                .size()
                .reset_index(name="Count")
                .pivot(index="Round", columns="Position", values="Count")
                .fillna(0)
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap="Blues", ax=ax)
            ax.set_title(f"{tier_option} — {week_option} Draft Position Frequency")
            st.pyplot(fig)
        
        # 🧠 TAB 3: Round 1 Anchor Analysis
        with tab3:
            st.header("🧠 Round 1 Anchor Analysis")
        
            anchor_pos = st.selectbox("Select Round 1 Anchor Position", ["RB", "WR", "QB", "TE"])
            tier_filter = st.selectbox("Percentile Tier", ["All Entries", "Top 1%", "Top 0.5%", "Top 0.1%"])
            week_filter = st.selectbox("Week Filter", ["All Weeks"] + sorted(entries_df["Week"].unique()))
            user_filter = st.text_input("Username Filter (optional)")
        
            anchor_df = entries_df.copy()
            if week_filter != "All Weeks":
                anchor_df = anchor_df[anchor_df["Week"] == week_filter]
            if tier_filter == "Top 1%":
                anchor_df = anchor_df[anchor_df["Top_1%"]]
            elif tier_filter == "Top 0.5%":
                anchor_df = anchor_df[anchor_df["Top_0.5%"]]
            elif tier_filter == "Top 0.1%":
                anchor_df = anchor_df[anchor_df["Top_0.1%"]]
            if user_filter:
                anchor_df = anchor_df[anchor_df["username"].str.lower() == user_filter.lower()]

            anchor_df = anchor_df[anchor_df["Pos 1"] == anchor_pos]

            melted = anchor_df.melt(
                value_vars=[f"Pos {i}" for i in range(2, 7)],
                var_name="Round",
                value_name="Position"
            )
            melted["Round"] = melted["Round"].str.extract(r"(\d)").astype(int)
        
            round_counts = (
                melted.groupby(["Round", "Position"])
                .size()
                .reset_index(name="Count")
                .pivot(index="Round", columns="Position", values="Count")
                .fillna(0)
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            round_counts.plot(kind="bar", stacked=True, ax=ax)
            ax.set_title(f"Draft Flow After Round 1 {anchor_pos} — {tier_filter} — {week_filter}")
            ax.set_xlabel("Draft Round")
            ax.set_ylabel("Count")
            ax.grid(axis="y")
            st.pyplot(fig)
                
