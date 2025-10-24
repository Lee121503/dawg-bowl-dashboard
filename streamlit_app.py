001 import streamlit as st
002 import pandas as pd
003 import matplotlib.pyplot as plt
004 from itertools import combinations

005 st.set_page_config(page_title="Dawg Bowl Contest Dashboard", layout="wide")

006 # 🔀 Sidebar mode selector
007 mode = st.sidebar.selectbox("Choose Mode", ["Dashboard", "Elite Trait Scanner"])

008 # 🔹 Shared Uploads
009 st.sidebar.header("📥 Upload Contest Files")
010 uploaded_weeks = st.sidebar.file_uploader("Upload weekly CSVs", type="csv", accept_multiple_files=True)
011 uploaded_positions = st.sidebar.file_uploader("Upload Position List Excel", type=["xls", "xlsx"])

012 # 🔹 Trait Scanner Function (must be defined outside Dashboard block)
013 def run_trait_scanner(uploaded_files):
014     st.title("🏆 Top 1% Draft Trait Scanner (By Week)")
015     if not uploaded_files:
016         st.info("📥 Please upload contest CSVs in the Dashboard tab first.")
017         return

018     for file in uploaded_files:
019         try:
020             df = pd.read_csv(file)
021             week_label = file.name.split("_Week_")[1].split("_")[0]
022         except Exception as e:
023             st.error(f"Error reading {file.name}: {e}")
024             continue

025         total_entries = len(df)
026         top_cutoff = max(1, int(total_entries * 0.01))
027         top_df = df.nsmallest(top_cutoff, "place")

028         st.subheader(f"📅 Week {week_label}")
029         st.markdown(f"**Total Entries:** {total_entries}  \n**Top 1% Cutoff:** Top {top_cutoff} entries")

030         all_players = pd.melt(df, id_vars=["place"], value_vars=[f"Player {i}" for i in range(1, 7)], var_name="Slot", value_name="Player")
031         top_players = pd.melt(top_df, id_vars=["place"], value_vars=[f"Player {i}" for i in range(1, 7)], var_name="Slot", value_name="Player")

032         player_counts = all_players["Player"].value_counts().rename("All Entries")
033         top_counts = top_players["Player"].value_counts().rename("Top 1%")

034         trait_df = pd.concat([top_counts, player_counts], axis=1).fillna(0)
035         trait_df["Elite Hit Rate (%)"] = (trait_df["Top 1%"] / trait_df["All Entries"]) * 100
036         trait_df = trait_df.sort_values("Elite Hit Rate (%)", ascending=False)

037         st.dataframe(trait_df.style.format({"Elite Hit Rate (%)": "{:.2f}"}))

038         # 🔗 Combo Detection
039         combo_records = []
040         for _, row in top_df.iterrows():
041             players = [row[f"Player {i}"] for i in range(1, 7)]
042             for pair in combinations(sorted(players), 2):
043                 combo_records.append(tuple(pair))
044         top_combo_counts = pd.Series(combo_records).value_counts().rename("Top 1%")

045         combo_records_all = []
046         for _, row in df.iterrows():
047             players = [row[f"Player {i}"] for i in range(1, 7)]
048             for pair in combinations(sorted(players), 2):
049                 combo_records_all.append(tuple(pair))
050         all_combo_counts = pd.Series(combo_records_all).value_counts().rename("All Entries")

051         combo_df = pd.concat([top_combo_counts, all_combo_counts], axis=1).fillna(0)
052         combo_df["Elite Hit Rate (%)"] = (combo_df["Top 1%"] / combo_df["All Entries"]) * 100
053         combo_df = combo_df.reset_index().rename(columns={"index": "Combo"})
054         combo_df[["Player A", "Player B"]] = pd.DataFrame(combo_df["Combo"].tolist(), index=combo_df.index)
055         combo_df = combo_df[["Player A", "Player B", "Top 1%", "All Entries", "Elite Hit Rate (%)"]]
056         combo_df = combo_df.sort_values("Elite Hit Rate (%)", ascending=False)

057         st.subheader("🔗 High-Impact Player Combos")
058         st.dataframe(combo_df.style.format({"Elite Hit Rate (%)": "{:.2f}"}))

059 # 🔹 Dashboard Mode
060 if mode == "Dashboard":
061     if uploaded_weeks and uploaded_positions:
062         all_weeks = []
063         for file in uploaded_weeks:
064             week_label = file.name.split("_Week_")[1].split("_")[0]
065             df = pd.read_csv(file)
066             df["Week"] = f"Week {week_label}"
067             all_weeks.append(df)
068         entries_df = pd.concat(all_weeks, ignore_index=True)

069         position_df = pd.read_excel(uploaded_positions)
070         position_map = dict(zip(position_df["Name"], position_df["Position"]))

071         for i in range(1, 7):
072             col = f"Player {i}"
073             pos_col = f"Pos {i}"
074             entries_df[pos_col] = entries_df[col].map(position_map).fillna("Unknown")

075         def assign_roles(row):
076             roles = {"QB Pick": None, "RB1 Pick": None, "WR1 Pick": None, "WR2 Pick": None, "TE Pick": None, "Flex Pick": None}
077             rb_count = wr_count = 0
078             used_slots = set()
079             for i in range(1, 7):
080                 pos = row[f"Pos {i}"]
081                 slot = i
082                 if pos == "QB" and not roles["QB Pick"]:
083                     roles["QB Pick"] = slot; used_slots.add(slot)
084                 elif pos == "RB" and rb_count < 1:
085                     roles["RB1 Pick"] = slot; rb_count += 1; used_slots.add(slot)
086                 elif pos == "WR" and wr_count < 2:
087                     if not roles["WR1 Pick"]: roles["WR1 Pick"] = slot
088                     else: roles["WR2 Pick"] = slot
089                     wr_count += 1; used_slots.add(slot)
090                 elif pos == "TE" and not roles["TE Pick"]:
091                     roles["TE Pick"] = slot; used_slots.add(slot)
092             for i in range(1, 7):
093                 pos = row[f"Pos {i}"]
094                 slot = i
095                 if slot not in used_slots and pos in ["RB", "WR", "TE"]:
096                     roles["Flex Pick"] = slot
097                     break
098             return pd.Series(roles)

099         entries_df = pd.concat([entries_df, entries_df.apply(assign_roles, axis=1)], axis=1)
100         entries_df["Total Entries"] = entries_df.groupby("username")["username"].transform("count")

101         def tag_percentile_tiers(df):
102             def tag_group(group):
103                 total = len(group)
104                 group["Top_0.1%"] = group["place"].astype(int) <= max(1, round(0.001 * total))
105                 group["Top_0.5%"] = group["place"].astype(int) <= max(1, round(0.005 * total))
106                 group["Top_1%"] = group["place"].astype(int) <= max(1, round(0.01 * total))
107                 return group
108             return df.groupby("Week", group_keys=False).apply(tag_group)

109         entries_df = tag_percentile_tiers(entries_df)

110         week_options = ["All Weeks"] + sorted(entries_df["Week"].unique())
111         selected_week = st.sidebar.selectbox("Filter by Week", week_options)
112         filtered_df = entries_df.copy()
113         if selected_week != "All Weeks":
114             filtered_df = filtered_df[filtered_df["Week"] == selected_week]

115         st.sidebar.header("🔍 Filter Users")
116         selected_user = st.sidebar.text_input("Username (optional)")
117         min_entries = st.sidebar.slider("Minimum Entries", 0, int(entries_df["Total Entries"].max()), 0)
118         sort_mode = st.sidebar.radio("Sort by", ["Elite Finish Count", "Elite Finish Rate"])

119         st.header("📊 User-Level Elite Finish Dashboard")
120         user_summary = (
121             filtered_df.groupby("username")[["Top_0.1%", "Top_0.5%", "Top_1%"]]
122             .sum()
123             .astype(int)
124             .join(filtered_df["username"].value_counts().rename("Total Entries"))
125             .reset_index()
126             .rename(columns={"index": "username"})
127         )

128         user_summary["Top 0.1% Rate"] = user_summary["Top_0.1%"] / user_summary["Total Entries"]
129         user_summary["Top 0.5% Rate"] = user_summary["Top_0.5%"] / user_summary["Total Entries"]
130         user_summary["Top 1% Rate"] = user_summary["Top_1%"] / user_summary["Total Entries"]

131         # 🔹 Apply filters
132         filtered = user_summary[user_summary["Total Entries"] >= min_entries]
133         if selected_user:
134             filtered = filtered[filtered["username"].str.lower() == selected_user.lower()]

135         # 🔹 Display with formatting
136         if sort_mode == "Elite Finish Count":
137             sort_cols = ["Top_0.1%", "Top_0.5%", "Top_1%"]
138         else:
139             sort_cols = ["Top 0.1% Rate", "Top 0.5% Rate", "Top 1% Rate"]

140         st.dataframe(
141             filtered.sort_values(by=sort_cols, ascending=False)
142             .style.format({
143                 "Top 0.1% Rate": "{:.2%}",
144                 "Top 0.5% Rate": "{:.2%}",
145                 "Top 1% Rate": "{:.2%}"
146             })
147         )

148         # 🔹 Export Button
149         st.download_button("📤 Export Filtered Table", filtered.to_csv(index=False), "filtered_user_summary.csv")

150         # 🔹 Weekly Draft Charts
151         st.header("🎛️ Weekly Draft Position Charts")
152         week_options = ["All Weeks"] + sorted(entries_df["Week"].unique())
153         selected_week = st.selectbox("Select Week", week_options)

154         if selected_week == "All Weeks":
155             week_df = entries_df.copy()
156             title_prefix = "All Weeks"
157         else:
158             week_df = entries_df[entries_df["Week"] == selected_week].copy()
159             title_prefix = selected_week

160         melted = week_df.melt(
161             id_vars=["place", "Top_0.1%", "Top_0.5%", "Top_1%"],
162             value_vars=[f"Pos {i}" for i in range(1, 7)],
163             var_name="Round",
164             value_name="Position"
165         )
166         melted["Round"] = melted["Round"].str.extract(r"(\d)").astype(int)

167         def plot_tier(tier_label):
168             tier_df = melted[melted[tier_label]]
169             count_df = tier_df.groupby(["Round", "Position"]).size().reset_index(name="Count")
170             pivot_df = count_df.pivot(index="Round", columns="Position", values="Count").fillna(0)
171             fig, ax = plt.subplots(figsize=(10, 6))
172             pivot_df.plot(kind="bar", stacked=False, ax=ax)
173             ax.set_title(f"{title_prefix} — {tier_label} Draft Position Frequency")
174             ax.set_xlabel("Draft Round")
175             ax.set_ylabel("Count")
176             ax.grid(axis="y")
177             st.pyplot(fig)

178         plot_tier("Top_0.1%")
179         plot_tier("Top_0.5%")
180         plot_tier("Top_1%")

181         # 🔹 Individual User Breakdown
182         st.header("🔍 Individual User Draft Breakdown")
183         user_input = st.text_input("Enter username for breakdown")
184         if user_input:
185             user_df = entries_df[entries_df["username"].str.lower() == user_input.lower()]
186             if not user_df.empty:
187                 st.subheader(f"📋 Summary for {user_input}")
188                 st.write(f"Total Entries: {len(user_df)}")
189                 st.write(f"Average Points: {user_df['points'].mean():.2f}")
190                 st.write(f"Top 0.1% Finishes: {user_df['Top_0.1%'].sum()}")
191                 st.write(f"Top 0.5% Finishes: {user_df['Top_0.5%'].sum()}")
192                 st.write(f"Top 1% Finishes: {user_df['Top_1%'].sum()}")
193                 st.dataframe(user_df[[
194                     "Week", "place", "points",
195                     "QB Pick", "RB1 Pick", "WR1 Pick", "WR2 Pick", "TE Pick", "Flex Pick"
196                 ]].sort_values(by=["Week", "place"]))
197             else:
198                 st.warning("No entries found for that username.")
199 # 🔹 Trait Scanner Mode Trigger
200 if mode == "Elite Trait Scanner":
201     run_trait_scanner(uploaded_weeks)
