from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_data_editor_cell_editor_closes_on_page_scroll() -> None:
    webdriver = pytest.importorskip("selenium.webdriver")
    common_by = pytest.importorskip("selenium.webdriver.common.by")
    action_chains = pytest.importorskip("selenium.webdriver.common.action_chains")
    chrome_options = pytest.importorskip("selenium.webdriver.chrome.options")
    selenium_exceptions = pytest.importorskip("selenium.common.exceptions")

    chrome_binary = find_chrome_binary()
    if chrome_binary is None:
        pytest.skip("Chrome is not installed")

    port = find_free_port()
    process = start_streamlit(port)
    driver = None
    try:
        wait_for_http(port)
        options = chrome_options.Options()
        options.binary_location = str(chrome_binary)
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,900")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        try:
            driver = webdriver.Chrome(options=options)
        except selenium_exceptions.WebDriverException as exc:
            pytest.skip(f"Chrome WebDriver is unavailable: {exc}")

        driver.get(f"http://127.0.0.1:{port}")
        wait_for_tabs(driver, common_by.By)
        driver.find_elements(common_by.By.CSS_SELECTOR, 'button[role="tab"]')[1].click()
        canvas = wait_for_canvas(driver, common_by.By)
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});', canvas)
        time.sleep(0.8)

        rect = driver.execute_script(
            "const r=arguments[0].getBoundingClientRect();"
            "return {x:r.x,y:r.y,width:r.width,height:r.height};",
            canvas,
        )
        action_chains.ActionChains(driver).move_by_offset(
            int(rect["x"] + 70),
            int(rect["y"] + 74),
        ).double_click().perform()
        action_chains.ActionChains(driver).move_by_offset(
            -int(rect["x"] + 70),
            -int(rect["y"] + 74),
        ).perform()
        wait_for_grid_editor(driver)
        before = grid_editor_snapshot(driver)

        driver.execute_script(
            "const main=document.querySelector('[data-testid=\"stMain\"]');"
            "main.scrollTop = Math.max(0, main.scrollTop - 300);"
            "main.dispatchEvent(new Event('scroll', {bubbles:true}));"
        )

        deadline = time.time() + 5
        after = grid_editor_snapshot(driver)
        while after["exists"] and time.time() < deadline:
            time.sleep(0.1)
            after = grid_editor_snapshot(driver)

        assert before["exists"] is True
        assert after["exists"] is False
    finally:
        if driver is not None:
            driver.quit()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def find_chrome_binary() -> Path | None:
    env_binary = os.environ.get("CHROME_BINARY")
    candidates = [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/google-chrome-stable"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/chromium-browser"),
    ]
    if env_binary:
        candidates.insert(0, Path(env_binary))
    return next((path for path in candidates if path.exists()), None)


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_streamlit(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless=true",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_http(port: int) -> None:
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 45
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(1)
    pytest.fail("Streamlit did not become ready")


def wait_for_tabs(driver, by) -> None:
    deadline = time.time() + 45
    while time.time() < deadline:
        tabs = driver.find_elements(by.CSS_SELECTOR, 'button[role="tab"]')
        if len(tabs) >= 3:
            return
        time.sleep(1)
    pytest.fail("Streamlit tabs did not render")


def wait_for_canvas(driver, by):
    deadline = time.time() + 45
    while time.time() < deadline:
        canvases = driver.find_elements(by.CSS_SELECTOR, '[data-testid="data-grid-canvas"]')
        if canvases:
            return canvases[0]
        time.sleep(1)
    pytest.fail("Data editor canvas did not render")


def wait_for_grid_editor(driver) -> None:
    deadline = time.time() + 5
    while time.time() < deadline:
        if grid_editor_snapshot(driver)["exists"]:
            return
        time.sleep(0.1)
    pytest.fail("Glide Data Grid editor did not open")


def grid_editor_snapshot(driver) -> dict:
    return driver.execute_script(
        """
        const editor = document.querySelector('.gdg-input');
        if (!editor) return {exists:false};
        const r = editor.getBoundingClientRect();
        return {
            exists: true,
            active: document.activeElement === editor,
            rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]
        };
        """
    )
