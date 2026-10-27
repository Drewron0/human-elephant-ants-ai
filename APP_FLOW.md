# Chess-Sut: application flow and code map

Read diagram 1 first, then follow the feature you want to study.
Each operation shows **plain-English behavior**, then **actual filename :: actual function**.
Decision diamonds describe conditions inside those functions. Arrows show execution,
button events, or data flow; this is a learning map, not a strict function-call graph.
Nested callbacks are marked explicitly. JSON boxes are stored data, not Python functions.

## 1. Starting the app and choosing a screen

```mermaid
flowchart TD
    Start["Run python main.py<br/>main.py :: main()"]
    DPI["Make the Windows interface sharp<br/>main.py :: enable_high_dpi()"]
    App["Create the window and session state<br/>gui.py :: GameApp.__init__()"]
    Theme["Configure shared widget styles<br/>ui_theme.py :: setup_ttk_styles()"]
    Router["Clean up the old screen and display the requested screen<br/>gui.py :: GameApp.show_view()"]
    Menu["Build the main menu<br/>views/menu_view.py :: MainMenuView._build_ui()"]
    Category["Choose Match Modes, Studio, or Records submenu<br/>views/menu_view.py :: MainMenuView._show_category()"]
    Setup["Configure PvE or PvP<br/>gui.py :: GameApp.open_config()<br/>views/config_view.py :: ConfigView.__init__()"]
    Puzzle["Browse puzzle stages<br/>views/puzzle_select_view.py :: PuzzleSelectView.__init__()"]
    Editor["Create or edit a stage<br/>views/stage_editor_view.py :: StageEditorView.__init__()"]
    Bench["Compare AI agents<br/>views/benchmark_view.py :: BenchmarkView.__init__()"]
    Scores["Read scores and records<br/>views/leaderboard_view.py :: LeaderboardView.__init__()"]
    Saves["Choose a saved match<br/>views/saves_view.py :: SavedGamesView.__init__()"]
    Guide["Read the rules<br/>views/tutorial_view.py :: TutorialView._build_ui()"]
    Quit["Close the application<br/>Tkinter library :: Tk.destroy()"]

    Start --> DPI --> App
    App --> Theme --> Router --> Menu
    Menu -->|Tactical Puzzle Mode| Puzzle
    Menu --> Category
    Category -->|Match Modes| Setup
    Category -->|Studio| Editor
    Category -->|Studio| Bench
    Category -->|Records| Scores
    Category -->|Records| Saves
    Category -->|Records| Guide
    Menu -->|Quit Application| Quit
```

`main()` also calls `app.mainloop()`, inherited from Tkinter. That event loop
handles clicks, repainting, timers, and scheduled callbacks for every screen.
Menu actions go through `GameApp.show_view()` or a small helper such as
`open_config()`. Submenu changes rebuild the menu itself.

## 2. Normal matches: player versus AI or player versus player

```mermaid
flowchart TD
    Setup["Read names, mode, timer, colors, and AI difficulty<br/>views/config_view.py :: ConfigView._start_game()"]
    Name["Remember the entered player name<br/>storage.py :: save_last_username()"]
    Launch["Open the match screen<br/>gui.py :: GameApp.start_game()"]
    Init["Create a board or restore a saved board<br/>views/game_view.py :: GameView.__init__()<br/>game_logic.py :: GameState.__init__() / GameState.from_dict()"]
    Click["Select a piece and destination<br/>views/game_view.py :: GameView._on_board_click()"]
    Legal["Find adjacent empty squares and permitted captures<br/>game_logic.py :: GameState.get_valid_moves_for_piece()"]
    Execute["Execute the selected move<br/>views/game_view.py :: GameView._execute_move()"]
    State["Store undo history, move or capture, check victory, swap turn<br/>game_logic.py :: GameState.make_move()"]
    Draw["Refresh board, turn, and move history<br/>views/game_view.py :: GameView._update_ui_state()"]
    Winner{"Has the game ended?"}
    Mode{"PvE and AI turn?"}
    AI["Calculate the computer move and display delay<br/>ai_engine.py :: get_ai_move_with_delay()"]
    Delay["Schedule execution of the AI move<br/>views/game_view.py :: GameView._execute_move()<br/>nested callback: _schedule_pve_ai()"]
    End["Stop timers, record the result, show the winner<br/>views/game_view.py :: GameView._handle_game_over()"]
    Clock["Count down the active player's clock<br/>views/game_view.py :: GameView._start_timer()"]
    Surrender["Confirm surrender<br/>views/game_view.py :: GameView._on_surrender()"]

    Setup --> Name --> Launch --> Init --> Click
    Init --> Clock
    Click --> Legal
    Legal -->|Click a valid destination| Execute
    Execute --> State --> Draw --> Winner
    Winner -->|Yes| End
    Winner -->|No| Mode
    Mode -->|Yes| AI --> Delay --> Execute
    Mode -->|No: next human turn| Click
    Clock -->|Clock expires| End
    Surrender --> End
```

The UI checks whether a clicked destination is legal before executing it.
`GameState.make_move()` applies the move; it is not a complete standalone
validator of movement distance. In local PvP, the two humans share this same
click-and-move flow. Network PvP adds diagram 7.

## 3. Puzzle selection and puzzle gameplay

```mermaid
flowchart TD
    Category["Choose preset, large, custom, or random stages<br/>views/puzzle_select_view.py :: PuzzleSelectView._set_category()"]
    Grid["Display stage thumbnails<br/>views/puzzle_select_view.py :: PuzzleSelectView._populate_grid()"]
    Select["Select a stage and show its details<br/>views/puzzle_select_view.py :: PuzzleSelectView._select_stage() / PuzzleSelectView._update_sidebar()"]
    Play["Read player name and AI model, then launch<br/>views/puzzle_select_view.py :: PuzzleSelectView._start_selected_stage()<br/>gui.py :: GameApp.start_puzzle()"]
    Init["Create the scenario board and attempt tracker<br/>views/puzzle_game_view.py :: PuzzleGameView.__init__()<br/>puzzle_logic.py :: PuzzleScenario.create_initial_state() / PuzzleSession.__init__()"]
    Click["Choose a legal player move<br/>views/puzzle_game_view.py :: PuzzleGameView._on_board_click()"]
    Move["Move the piece and count one player step<br/>views/puzzle_game_view.py :: PuzzleGameView._execute_player_move()<br/>game_logic.py :: GameState.make_move()<br/>puzzle_logic.py :: PuzzleSession.record_player_step()"]
    Status["Check target, remaining pieces, legal moves, and step limit<br/>puzzle_logic.py :: PuzzleSession.evaluate_status()"]
    Result{"Solved or neutralized?"}
    AI["Request the defender's move<br/>views/puzzle_game_view.py :: PuzzleGameView._trigger_ai_move()<br/>ai_engine.py :: get_defender_move()"]
    HasMove{"Does the defender have a move?"}
    Reply["Record search metrics and schedule the AI move<br/>puzzle_logic.py :: PuzzleSession.record_ai_telemetry()<br/>views/puzzle_game_view.py :: PuzzleGameView._trigger_ai_move()<br/>nested callback: do_move()"]
    Finish["Show puzzle outcome; save a score when solved<br/>views/puzzle_game_view.py :: PuzzleGameView._handle_puzzle_finish()"]
    Score["Write the stage score<br/>storage.py :: save_stage_score()"]

    Category --> Grid --> Select --> Play --> Init --> Click --> Move --> Status
    Status --> Result
    Result -->|Yes| Finish
    Result -->|No, after player move| AI --> HasMove
    HasMove -->|No: puzzle treated as solved| Finish
    HasMove -->|Yes| Reply --> Status
    Result -->|No, after AI move| Click
    Finish -->|Solved| Score
```

Only player moves count toward the puzzle limit. `PuzzleScenario.__init__()`
sets `s_max = 3 * s_optimal`. The AI's reply does not consume a player step.

## 4. Random Challenge: background work and a responsive interface

```mermaid
flowchart TD
    Click["Open Random Challenge<br/>views/puzzle_select_view.py :: PuzzleSelectView._set_category()"]
    Cached{"Does the app already have a completed batch?"}
    Render["Display cached challenge cards or a generation error<br/>views/puzzle_select_view.py :: PuzzleSelectView._populate_grid()"]
    Running{"Is a generation job already running?"}
    Loading["Show Creating Random Challenge.....; keep navigation available<br/>views/puzzle_select_view.py :: PuzzleSelectView._populate_grid()"]
    Start["Start one daemon worker thread<br/>views/puzzle_select_view.py :: PuzzleSelectView._set_category()"]
    Worker["Generate three puzzles sequentially; catch errors<br/>views/puzzle_select_view.py :: _generate_random_challenges()"]
    Generator["Generate and check candidate boards<br/>puzzle_logic.py :: generate_winnable_puzzle()"]
    Inbox["Put the completed batch or error in the app's queue<br/>views/puzzle_select_view.py :: _generate_random_challenges()<br/>queue library :: Queue.put()"]
    Poll["Main thread checks the queue without waiting<br/>views/puzzle_select_view.py :: PuzzleSelectView._poll_random_challenges()"]
    Empty{"Queue empty?"}
    Later["Schedule another check in 100 ms<br/>Tkinter library :: after()"]
    Store["Cache results or error and clear the loading flag<br/>views/puzzle_select_view.py :: PuzzleSelectView._poll_random_challenges()"]
    Active{"Is Random Challenge still the active tab?"}
    Stay["Keep the user's current tab unchanged"]
    Leave["Leave or destroy the selector; cancel its polling callback<br/>views/puzzle_select_view.py :: PuzzleSelectView._cleanup() / PuzzleSelectView.destroy()"]
    Reopen["Reopen the selector and resume checking a running job<br/>views/puzzle_select_view.py :: PuzzleSelectView.__init__()"]

    Click --> Cached
    Cached -->|Yes| Render
    Cached -->|No| Running
    Running -->|Yes: reuse job| Loading
    Running -->|No: new job or retry| Loading
    Loading -->|Only if starting a new job| Start --> Worker --> Generator --> Inbox
    Loading --> Poll --> Empty
    Empty -->|Yes| Later --> Poll
    Empty -->|No| Store --> Active
    Active -->|Yes: cards or error message| Render
    Active -->|No| Stay
    Loading -.->|User navigates away| Leave
    Leave -.->|Worker continues independently| Worker
    Leave -.->|User returns| Reopen --> Poll
    Inbox -.->|Result available| Poll
```

The queue and cached batch belong to `GameApp`, initialized in
`gui.py :: GameApp.__init__()`. They survive replacing the selection screen.
The worker never changes widgets. Polling belongs to the screen and stops when
that screen is destroyed. Returning after a failure starts a retry when the
user selects Random Challenge again.

## 5. Stage editor and puzzle verification

```mermaid
flowchart TD
    Open["Open a new or existing custom stage<br/>views/stage_editor_view.py :: StageEditorView.__init__()"]
    Edit["Place or erase a piece<br/>views/stage_editor_view.py :: StageEditorView._on_canvas_click() / StageEditorView._on_canvas_right_click()"]
    Reset["Resize the board or reset its pieces<br/>views/stage_editor_view.py :: StageEditorView._on_size_change() / StageEditorView._clear_board()"]
    Unverified["Clear the previous check and mark Unverified<br/>views/stage_editor_view.py :: StageEditorView._invalidate_verification()"]
    Check["Verify the board on request<br/>views/stage_editor_view.py :: StageEditorView._verify_winnability()"]
    Save["Click Save Stage; run verification again<br/>views/stage_editor_view.py :: StageEditorView._save_stage()"]
    HasPlayer{"At least one player piece?"}
    Search["Search for a winning route<br/>puzzle_logic.py :: find_optimal_winning_path()"]
    Adversarial["Search player moves with simulated defender replies<br/>puzzle_logic.py :: solve_adversarial_optimal_path()"]
    Found{"Did the adversarial search find a route?"}
    BFS["Fallback: search a route with stationary opponents<br/>puzzle_logic.py :: bfs_safe_path()"]
    Outcome{"Was a route found?"}
    Good["Store route and step count; display move limit = 3 times steps<br/>views/stage_editor_view.py :: StageEditorView._verify_winnability()"]
    Bad["Display verification failure; block saving<br/>views/stage_editor_view.py :: StageEditorView._verify_winnability() / StageEditorView._save_stage()"]
    Persist["Write custom stage and return to selection<br/>storage.py :: save_custom_stage()<br/>gui.py :: GameApp.show_view()"]
    Delete["Confirm deletion and remove the stage<br/>views/stage_editor_view.py :: StageEditorView._delete_stage()<br/>storage.py :: delete_custom_stage()"]

    Open --> Edit --> Unverified
    Open --> Reset --> Unverified
    Unverified -->|Keep editing, no automatic search| Edit
    Unverified -->|Verify button| Check
    Unverified -->|Save button| Save
    Check --> HasPlayer
    Save --> Check
    HasPlayer -->|No| Bad
    HasPlayer -->|Yes| Search --> Adversarial --> Found
    Found -->|Yes| Good
    Found -->|No| BFS --> Outcome
    Outcome -->|Yes| Good
    Outcome -->|No| Bad
    Good -->|If called from Save Stage| Persist
    Good -->|If called from Verify button| Edit
    Open -->|Delete existing stage| Delete
```

Editing no longer launches the solver automatically. Manual verification and
Save Stage still calculate on the UI thread. The search is bounded and has a
static fallback, so the displayed step count is not a proof of the shortest
route against perfect defense.

## 6. How the AI chooses a move

```mermaid
flowchart TD
    Match["Normal PvE requests a move<br/>ai_engine.py :: get_ai_move_with_delay()"]
    Engine["Select the standard difficulty or proposed engine<br/>ai_engine.py :: AIEngine.get_move_and_delay()"]
    Easy["Easy: score immediate results, sometimes choose another top move<br/>ai_engine.py :: evaluate_board()"]
    Standard["Normal: depth 2; Hard: depth 3<br/>ai_engine.py :: minimax()"]
    StandardOrder["Order promising moves before searching<br/>ai_engine.py :: order_moves()"]
    StandardEval["Score piece values and progress toward the target<br/>ai_engine.py :: evaluate_board()"]
    Defender["Puzzle, verification, benchmark, or proposed PvE requests a defender move<br/>ai_engine.py :: get_defender_move()"]
    Model{"Which defender model?"}
    Random["Choose a random legal move<br/>Python random library :: choice()"]
    Vanilla["Search without alpha-beta pruning<br/>ai_engine.py :: _minimax_vanilla_internal()"]
    Static["Score fixed piece values<br/>ai_engine.py :: _evaluate_static_material()"]
    Optimized["Search with alpha-beta pruning and a time budget<br/>ai_engine.py :: _minimax_ab_internal()"]
    Order["Prioritize valuable captures and progress<br/>ai_engine.py :: order_moves_mvv_lva()"]
    Evaluate["Score matchups, threats, mobility, and target progress<br/>ai_engine.py :: evaluate_non_transitive()"]
    Return["Return the chosen move to the caller"]

    Match --> Engine
    Engine -->|Easy| Easy --> Return
    Engine -->|Normal or Hard| Standard --> StandardOrder --> StandardEval --> Return
    Engine -->|Proposed| Defender
    Defender --> Model
    Model -->|Random baseline| Random --> Return
    Model -->|Vanilla baseline| Vanilla --> Static --> Return
    Model -->|Proposed alpha-beta| Optimized --> Order --> Evaluate --> Return
```

This diagram summarizes recursive search; it does not show every recursive call.
Both move entry points also check for an immediately winning move before their
normal difficulty/model branches. `get_defender_move()` additionally returns
an evaluation score and `SearchTelemetry` metrics.

## 7. Network multiplayer

```mermaid
flowchart TD
    Config["Choose host or join, IP address, and port<br/>views/config_view.py :: ConfigView._start_game()"]
    Init["Connect the game callbacks to networking<br/>views/game_view.py :: GameView._init_network()"]
    Start["Start the network worker thread<br/>network.py :: NetworkManager.start()"]
    Network["Accept or connect; receive newline-separated JSON messages<br/>network.py :: NetworkManager._run_network()"]
    Dispatch["Identify the incoming message type<br/>network.py :: NetworkManager._handle_message()"]
    Name["Show the opponent's name on the main thread<br/>views/game_view.py :: GameView._on_opponent_named()"]
    Remote["Schedule the remote move on the main thread<br/>views/game_view.py :: GameView._execute_move()"]
    Local["Make a local move<br/>views/game_view.py :: GameView._execute_move()"]
    Send["Send source and destination coordinates<br/>network.py :: NetworkManager.send_move() / NetworkManager._send()"]
    Restart["Handle a remote restart or surrender<br/>views/game_view.py :: GameView._restart_match() / GameView._handle_game_over()"]
    Close["Close the connection when leaving<br/>views/game_view.py :: GameView._cleanup()<br/>network.py :: NetworkManager.close()"]

    Config --> Init --> Start --> Network --> Dispatch
    Dispatch -->|NAME| Name
    Dispatch -->|MOVE| Remote
    Dispatch -->|RESTART or SURRENDER| Restart
    Local --> Send -.->|Other computer receives it| Network
    Init -.->|Leave screen| Close
```

Network callbacks use `self.after(0, ...)` to schedule UI work.
Remote moves pass `from_network=True` so they are not sent back to the peer.

## 8. Player profiles, scores, and saved matches

```mermaid
flowchart TD
    Profiles["Read remembered player names<br/>storage.py :: get_last_username() / get_recent_profiles()"]
    Remember["Remember a name when starting a match or puzzle<br/>storage.py :: save_last_username()"]
    ProfileFile[("app_config.json")]
    Finish["A match ends<br/>views/game_view.py :: GameView._handle_game_over()"]
    PvE["Record a human PvE win<br/>storage.py :: save_pve_score()"]
    PvP["Update both PvP players' wins or losses<br/>storage.py :: update_pvp_stats()"]
    Puzzle["A puzzle is solved<br/>views/puzzle_game_view.py :: PuzzleGameView._handle_puzzle_finish()"]
    StageScore["Record the stage result<br/>storage.py :: save_stage_score()"]
    Scores[("leaderboard.json")]
    Table["Read and display match leaderboards<br/>views/leaderboard_view.py :: LeaderboardView._refresh_table()<br/>storage.py :: get_pve_leaderboard() / get_pvp_stats()"]
    StageTable["Read and display a stage leaderboard<br/>views/puzzle_select_view.py :: PuzzleSelectView._refresh_stage_leaderboard()<br/>storage.py :: get_stage_leaderboard()"]
    Save["Choose a PvE save slot<br/>views/game_view.py :: GameView._on_save()<br/>nested callback: make_save_cmd()"]
    Serialize["Convert the board state to JSON-ready data and save it<br/>game_logic.py :: GameState.to_dict()<br/>storage.py :: save_game_slot()"]
    Saves[("saved_games.json")]
    List["List saved slots<br/>views/saves_view.py :: SavedGamesView._refresh_slots()<br/>storage.py :: get_saved_slots()"]
    Load["Load the chosen match<br/>views/saves_view.py :: SavedGamesView._refresh_slots()<br/>nested callback: make_load_cmd()<br/>gui.py :: GameApp.start_game()"]
    Restore["Restore board, names, and clocks<br/>views/game_view.py :: GameView.__init__()<br/>game_logic.py :: GameState.from_dict()"]
    Custom[("custom_stages.json")]
    CustomList["Load custom stages into the stage catalog<br/>storage.py :: get_custom_stages()<br/>puzzle_logic.py :: get_all_puzzles()<br/>views/puzzle_select_view.py :: PuzzleSelectView._populate_grid()"]

    ProfileFile --> Profiles
    Remember --> ProfileFile
    Finish -->|PvE human wins| PvE --> Scores
    Finish -->|PvP| PvP --> Scores
    Puzzle --> StageScore --> Scores
    Scores --> Table
    Scores --> StageTable
    Save --> Serialize --> Saves --> List --> Load --> Restore
    Custom --> CustomList
```

All four JSON files are local runtime data. `storage._load_json()` and
`storage._save_json()` handle the common file operations. Guest mode is removed;
old guest names remain ordinary names. The recent-profile list retains up to
10 names. Custom stages are loaded through `puzzle_logic.get_all_puzzles()`;
they are not leaderboard records.

## 9. Benchmark lab and standalone developer tools

```mermaid
flowchart TD
    Single["Start one benchmark configuration<br/>views/benchmark_view.py :: BenchmarkView._start_single_benchmark()"]
    Full["Start the comparison batch<br/>views/benchmark_view.py :: BenchmarkView._start_full_benchmark()"]
    Worker["Run simulations in a worker thread<br/>views/benchmark_view.py :: BenchmarkView._start_single_benchmark()<br/>nested callback: worker()"]
    Sim["Repeat scripted-player moves against defender AI<br/>puzzle_logic.py :: run_simulation_benchmark()"]
    Player["Choose the simulated player's move<br/>puzzle_logic.py :: ShortestPathScriptedPlayer.select_move() / SubOptimalScriptedPlayer.select_move() / RandomScriptedPlayer.select_move()"]
    Defender["Choose the defender's reply<br/>ai_engine.py :: get_defender_move()"]
    Board["Apply each move and check the winner<br/>game_logic.py :: GameState.make_move()"]
    Progress["Update benchmark progress<br/>views/benchmark_view.py :: BenchmarkView._update_progress()"]
    Result["Show latency, pruning, delay, and neutralization results<br/>views/benchmark_view.py :: BenchmarkView._on_benchmark_complete()"]
    Export["Export the displayed results<br/>views/benchmark_view.py :: BenchmarkView._export_csv()"]
    CLI["Run benchmarks from the terminal<br/>run_benchmark.py :: main()"]
    Verify["Check preset and generated stages from the terminal<br/>verify_stages.py :: main()"]
    Presets["Verify preset stage routes<br/>verify_stages.py :: verify_preset_stages()"]
    Random["Verify randomly generated stage routes<br/>verify_stages.py :: verify_random_generator()"]

    Single --> Worker --> Sim
    Full -->|Its own nested worker callback| Sim
    CLI --> Sim
    Sim --> Player --> Board
    Sim --> Defender --> Board
    Sim -.->|Progress callback| Progress
    Sim -->|Finished GUI run| Result --> Export
    Verify --> Presets
    Verify --> Random
```

Unlike the GUI benchmark, `run_benchmark.py` prints results to the terminal.
The verification script calls the same puzzle-search functions described in
diagram 5. Tests are separate checks under `tests/`, not part of normal startup.

## Important distinctions when explaining this app

- **Screen:** a Tkinter frame, usually one class in `views/`.
- **Controller:** `GameApp` chooses which screen exists at a given time.
- **State:** `GameState` holds the board, turn, history, and winner.
- **AI:** search code in `ai_engine.py` chooses moves; it does not draw the board.
- **Worker thread:** explicitly created by `threading.Thread(...)` for random
  generation, networking, and GUI benchmarks.
- **Scheduled callback:** `after(...)` runs later on the UI thread. Scheduling
  an expensive calculation this way does not make it background work.
- **Queue:** random-generation results travel from the worker to the UI through
  the application-owned `random_challenge_queue`.
- **Current limitation:** normal-match AI, puzzle defender search, and manual
  stage verification still calculate on the UI thread.
