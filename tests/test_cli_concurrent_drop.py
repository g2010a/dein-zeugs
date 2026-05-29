import os
import fcntl
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["DEIN_ZEUGS_NO_OPEN"] = "1"


def make_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "dein_zeugs_root"
    for d in ["inbox", "analysis", "aired", "reports"]:
        (root / d).mkdir(parents=True)
    for i in range(3):
        (root / "inbox" / f"caller_{i:03d}.mp3").touch()
    return root


def test_concurrent_lock_contention(tmp_path):
    """When two instances try to acquire the lock simultaneously, only one succeeds.
    The loser exits 0 immediately; the winner does one drain pass and renders the report.

    We use a threading.Event to guarantee the two flock attempts overlap:
    - Thread 1 (winner) acquires the lock then signals it holds it.
    - Thread 2 (loser) waits until thread 1 holds the lock, then tries to acquire — gets OSError.
    """
    root = make_fixture_root(tmp_path)

    render_count = [0]
    render_lock = threading.Lock()

    # winner_holds is set when thread-1 has acquired the flock
    winner_holds = threading.Event()
    # winner_done is set when thread-1 is about to release the flock
    winner_done = threading.Event()

    # Tracks which thread holds the simulated lock
    flock_state = {"held": False}
    flock_state_lock = threading.Lock()

    def fake_flock(fd, op):
        if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
            with flock_state_lock:
                if flock_state["held"]:
                    raise OSError("Resource temporarily unavailable")
                flock_state["held"] = True
            # Signal that a winner has the lock so the loser thread can proceed
            winner_holds.set()
            # Hold until winner is done (simulate work duration)
            winner_done.wait(timeout=5)
        elif op == fcntl.LOCK_UN:
            with flock_state_lock:
                flock_state["held"] = False

    def mock_process(paths, config, embedding_model):
        return 0

    def mock_render(paths, config):
        with render_lock:
            render_count[0] += 1
        report = paths.reports / "report.html"
        report.write_text("<html>ok</html>")
        winner_done.set()  # signal winner is done after rendering
        return report

    mock_embedding = MagicMock()
    results = []
    results_lock = threading.Lock()

    from dein_zeugs.cli import main

    def run_winner():
        result = main([str(root)])
        with results_lock:
            results.append(("winner", result))

    def run_loser():
        # Wait until winner holds the lock before trying to acquire
        winner_holds.wait(timeout=5)
        result = main([str(root)])
        with results_lock:
            results.append(("loser", result))

    with patch("fcntl.flock", side_effect=fake_flock), \
         patch("dein_zeugs.cli.ensure_llm_model"), \
         patch("dein_zeugs.cli.process_all_unprocessed", side_effect=mock_process), \
         patch("dein_zeugs.cli.render_report", side_effect=mock_render), \
         patch("dein_zeugs.cli.EmbeddingModel", return_value=mock_embedding):

        t1 = threading.Thread(target=run_winner, name="winner")
        t2 = threading.Thread(target=run_loser, name="loser")
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

    assert len(results) == 2, f"Not all threads completed: {results}"
    exit_codes = {name: code for name, code in results}
    assert exit_codes.get("winner") == 0, f"Winner exited non-zero: {exit_codes}"
    assert exit_codes.get("loser") == 0, f"Loser should exit 0 (lock contention): {exit_codes}"

    # Only the winner renders the report
    assert render_count[0] == 1, f"render called {render_count[0]} times, expected 1"


def test_concurrent_all_files_processed(tmp_path):
    """Simulates the scenario described in the spec: N files dropped simultaneously.
    The lock-holder's drain loop processes all files; the loser exits immediately.
    This test verifies drain loop correctness with patched flock.
    """
    root = make_fixture_root(tmp_path)

    processed_files = []
    drain_counts = [0]

    flock_lock = threading.Lock()
    lock_held = [False]

    def fake_flock(fd, op):
        if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
            with flock_lock:
                if lock_held[0]:
                    raise OSError("locked")
                lock_held[0] = True
        elif op == fcntl.LOCK_UN:
            with flock_lock:
                lock_held[0] = False

    call_number = [0]

    def mock_process(paths, config, embedding_model):
        n = call_number[0]
        call_number[0] += 1
        drain_counts[0] += 1
        if n == 0:
            # First pass: process all 3 files
            for mp3 in sorted(paths.inbox.glob("*.mp3")):
                yaml_path = paths.analysis / (mp3.stem + ".yaml")
                yaml_path.write_text(f"stem: {mp3.stem}\n")
                processed_files.append(mp3.stem)
            return 3
        return 0  # subsequent passes: nothing to do

    def mock_render(paths, config):
        report = paths.reports / "report.html"
        report.write_text("<html>ok</html>")
        return report

    mock_embedding = MagicMock()

    with patch("fcntl.flock", side_effect=fake_flock), \
         patch("dein_zeugs.cli.ensure_llm_model"), \
         patch("dein_zeugs.cli.process_all_unprocessed", side_effect=mock_process), \
         patch("dein_zeugs.cli.render_report", side_effect=mock_render), \
         patch("dein_zeugs.cli.EmbeddingModel", return_value=mock_embedding):

        from dein_zeugs.cli import main
        result = main([str(root)])

    assert result == 0
    assert len(processed_files) == 3
    assert set(processed_files) == {"caller_000", "caller_001", "caller_002"}
