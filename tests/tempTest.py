import re
from playwright.sync_api import Page, expect


def test_example(page: Page) -> None:
    page.goto("https://ai-assistant-t0m0.onrender.com/")
    page.get_by_text("AI Academic AssistantAskRecommendationsPDF toolsLog in Study smarter with your").click()
    page.get_by_role("link", name="Create an account").click()
    page.get_by_role("paragraph").get_by_role("link", name="Log in").click()
    page.get_by_role("textbox", name="Username").click()
    page.get_by_role("textbox", name="Username").press("CapsLock")
    page.get_by_role("textbox", name="Username").fill("Admin")
    page.get_by_role("textbox", name="Username").press("Tab")
    page.get_by_role("textbox", name="Password").press("CapsLock")
    page.get_by_role("textbox", name="Password").fill("password")
    page.get_by_role("button", name="Log in").click()
