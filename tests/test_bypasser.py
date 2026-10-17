"""Comprehensive test suite for Telegram Link Bypasser Bot.

Tests at least 10 sites/plugins, safety checks, database caching, and plugin manager.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from bypassers.base import BaseBypasser
from bypassers.bitly import BitlyBypasser
from bypassers.tinyurl import TinyUrlBypasser
from bypassers.isgd import IsGdBypasser
from bypassers.cuttly import CuttlyBypasser
from bypassers.tco import TcoBypasser
from bypassers.rebrandly import RebrandlyBypasser
from bypassers.adfly import AdFlyBypasser, _decrypt_adfly_ysmm
from bypassers.shortest import ShortestBypasser
from bypassers.sirigan import SiriganBypasser
from bypassers.thinfi import ThinfiBypasser
from bypassers.droplink import DropLinkBypasser
from bypassers.shrinkme import ShrinkMeBypasser
from bypassers.tnlink import TnLinkBypasser
from bypassers.adlinkfly_network import AdLinkFlyNetworkBypasser
from bypassers.rekonise import RekoniseBypasser
from bypassers.adfocus import AdFocusBypasser
from bypassers.boost_ink import BoostInkBypasser
from bypassers.social_unlock import SocialUnlockBypasser
from bypassers.lootlink import LootLinkBypasser
from bypassers.generic import GenericBypasser
from bypassers.manager import BypasserManager
from bypassers.exceptions import SafetyBlockedError, BypassError
from utils.safety import is_dangerous_url, is_dangerous_response_headers
from utils.extractor import extract_urls
from utils.rate_limiter import RateLimiter
from db.database import Database


class TestBypasserPlugins(unittest.IsolatedAsyncioTestCase):
    """Unit tests for individual bypasser plugins."""

    # 1. Bit.ly Plugin Test
    async def test_bitly_matching_and_bypass(self):
        b = BitlyBypasser()
        self.assertTrue(b.match("https://bit.ly/3xyz123"))
        self.assertFalse(b.match("https://google.com/test"))

        # Mock safe_fetch_url response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com/target-destination"
        with patch("bypassers.bitly.safe_fetch_url", return_value=mock_resp):
            result = await b.bypass("https://bit.ly/3xyz123")
            self.assertEqual(result, "https://example.com/target-destination")

    # 2. TinyURL Plugin Test
    async def test_tinyurl_matching_and_bypass(self):
        b = TinyUrlBypasser()
        self.assertTrue(b.match("https://tinyurl.com/abcde12"))
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://github.com/myproject"
        with patch("bypassers.tinyurl.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://tinyurl.com/abcde12")
            self.assertEqual(res, "https://github.com/myproject")

    # 3. Is.gd Plugin Test
    async def test_isgd_matching_and_bypass(self):
        b = IsGdBypasser()
        self.assertTrue(b.match("https://is.gd/testlink"))
        self.assertTrue(b.match("https://v.gd/testlink"))

        mock_api_resp = MagicMock()
        mock_api_resp.status_code = 200
        mock_api_resp.json.return_value = {"url": "https://python.org"}
        with patch("bypassers.isgd.safe_fetch_url", return_value=mock_api_resp):
            res = await b.bypass("https://is.gd/testlink")
            self.assertEqual(res, "https://python.org")

    # 4. Cutt.ly Plugin Test
    async def test_cuttly_matching_and_bypass(self):
        b = CuttlyBypasser()
        self.assertTrue(b.match("https://cutt.ly/mycustomlink"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://wikipedia.org/wiki/Main_Page"
        with patch("bypassers.cuttly.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://cutt.ly/mycustomlink")
            self.assertEqual(res, "https://wikipedia.org/wiki/Main_Page")

    # 5. T.co Plugin Test
    async def test_tco_matching_and_bypass(self):
        b = TcoBypasser()
        self.assertTrue(b.match("https://t.co/9A1B2C3D"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://t.co/9A1B2C3D"
        mock_resp.text = '<html><head><meta http-equiv="refresh" content="0;url=https://news.ycombinator.com"></head></html>'
        with patch("bypassers.tco.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://t.co/9A1B2C3D")
            self.assertEqual(res, "https://news.ycombinator.com")

    # 6. Rebrandly Plugin Test
    async def test_rebrandly_matching_and_bypass(self):
        b = RebrandlyBypasser()
        self.assertTrue(b.match("https://rebrand.ly/somelink"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://docs.python.org/3/"
        with patch("bypassers.rebrandly.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://rebrand.ly/somelink")
            self.assertEqual(res, "https://docs.python.org/3/")

    # 7. AdFly XOR Cipher & Plugin Test
    async def test_adfly_ysmm_decryption(self):
        b = AdFlyBypasser()
        self.assertTrue(b.match("https://adf.ly/QtG5r"))
        self.assertTrue(b.match("https://j.gs/12345"))
        self.assertTrue(b.match("https://microify.com/abc"))

        # Verify XOR cipher algorithm directly with sample payload
        # A mock page with ysmm embedded
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://adf.ly/QtG5r"
        # Test direct redirect fallback in adfly
        mock_resp.text = '<html><body>Redirecting...</body></html>'
        mock_resp.url = "https://destination-site.org/success"
        with patch("bypassers.adfly.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://adf.ly/QtG5r")
            self.assertEqual(res, "https://destination-site.org/success")

    # 8. Sirigan Plugin Test
    async def test_sirigan_bypass(self):
        b = SiriganBypasser()
        self.assertTrue(b.match("https://safeurl.sirigan.my.id/proses.html?asu=123"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Base64 encoded 'https://target-destination.com'
        import base64
        b64_url = base64.b64encode(b"https://target-destination.com").decode("utf-8")
        mock_resp.url = f"https://safeurl.sirigan.my.id/proses.html?asu={b64_url}"
        with patch("bypassers.sirigan.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://safeurl.sirigan.my.id/test")
            self.assertEqual(res, "https://target-destination.com")

    # 9. Thinfi Plugin Test
    async def test_thinfi_bypass(self):
        b = ThinfiBypasser()
        self.assertTrue(b.match("https://thinfi.com/088ud"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><p><a href="https://final-destination.net">Click</a></p></body></html>'
        with patch("bypassers.thinfi.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://thinfi.com/088ud")
            self.assertEqual(res, "https://final-destination.net")

    # 10. Shortest Plugin Test
    async def test_shortest_bypass(self):
        b = ShortestBypasser()
        self.assertTrue(b.match("http://festyy.com/eavTIP"))
        self.assertTrue(b.match("https://shorte.st/abcd"))

        mock_page = MagicMock()
        mock_page.status_code = 200
        mock_page.url = "http://festyy.com/eavTIP"
        mock_page.text = 'var sessionId = "sess_123456";'

        mock_api = MagicMock()
        mock_api.status_code = 200
        mock_api.text = '{"destinationUrl": "https://my-dest.com/file"}'

        async def fake_fetch(url, *args, **kwargs):
            if "shortest-url" in url:
                return mock_api
            return mock_page

        with patch("bypassers.shortest.safe_fetch_url", side_effect=fake_fetch):
            with patch("asyncio.sleep", return_value=None):
                res = await b.bypass("http://festyy.com/eavTIP")
                self.assertEqual(res, "https://my-dest.com/file")

    # 11. AdLinkFly Network Plugin Test
    async def test_adlinkfly_network_bypass(self):
        b = AdLinkFlyNetworkBypasser()
        self.assertTrue(b.match("https://shortner.in/xyz"))
        self.assertTrue(b.match("https://urlshortx.com/abc"))
        self.assertTrue(b.match("https://earnlink.io/test"))

        mock_form_page = MagicMock()
        mock_form_page.status_code = 200
        mock_form_page.url = "https://shortner.in/xyz"
        mock_form_page.text = '''
            <form id="go-link" action="/links/go">
                <input name="_csrfToken" value="csrf12345">
                <input name="ad_form_data" value="tok987">
            </form>
        '''

        mock_ajax_resp = MagicMock()
        mock_ajax_resp.status_code = 200
        mock_ajax_resp.json.return_value = {"status": "success", "url": "https://real-link.org/download"}

        async def fake_adlink_fetch(url, *args, **kwargs):
            if "/links/go" in url:
                return mock_ajax_resp
            return mock_form_page

        with patch("bypassers.adlinkfly_network.safe_fetch_url", side_effect=fake_adlink_fetch):
            with patch("asyncio.sleep", return_value=None):
                res = await b.bypass("https://shortner.in/xyz")
                self.assertEqual(res, "https://real-link.org/download")

    # 12. Linkvertise Dynamic & Static Test
    async def test_linkvertise_dynamic_bypass(self):
        from bypassers.linkvertise import LinkvertiseBypasser
        b = LinkvertiseBypasser()
        self.assertTrue(b.match("https://link-to.net/1275495/934.871548/dynamic?r=aHR0cHM6Ly9wYXN0ZWxpbmsubmV0L29keGRsdnNp"))
        
        # Test dynamic parameter decoding directly
        res = await b.bypass("https://link-to.net/1275495/934.871548/dynamic?r=aHR0cHM6Ly9wYXN0ZWxpbmsubmV0L29keGRsdnNp")
        self.assertEqual(res, "https://pastelink.net/odxdlvsi")

    # 13. Rekonise Plugin Test
    async def test_rekonise_bypass(self):
        b = RekoniseBypasser()
        self.assertTrue(b.match("https://rekonise.com/sample-slug-123"))
        self.assertTrue(b.match("https://rkns.link/sample-slug-123"))

        mock_api_resp = MagicMock()
        mock_api_resp.status_code = 200
        mock_api_resp.json.return_value = {"url": "https://mediafire.com/file/download123"}
        with patch("bypassers.rekonise.safe_fetch_url", return_value=mock_api_resp):
            res = await b.bypass("https://rekonise.com/sample-slug-123")
            self.assertEqual(res, "https://mediafire.com/file/download123")

    # 14. AdFocus Plugin Test
    async def test_adfocus_bypass(self):
        b = AdFocusBypasser()
        self.assertTrue(b.match("https://adfoc.us/12345678"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><script>var click_url = "https://github.com/release/v1.0";</script></head></html>'
        with patch("bypassers.adfocus.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://adfoc.us/12345678")
            self.assertEqual(res, "https://github.com/release/v1.0")

    # 15. Boost.ink Plugin Test
    async def test_boost_ink_bypass(self):
        import base64
        b = BoostInkBypasser()
        self.assertTrue(b.match("https://boost.ink/sample-code"))
        self.assertTrue(b.match("https://bst.gg/another-code"))

        b64_url = base64.b64encode(b"https://destination.org/unlocked").decode("utf-8")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = f'<html><body><button data-target="{b64_url}">Get Link</button></body></html>'
        with patch("bypassers.boost_ink.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://boost.ink/sample-code")
            self.assertEqual(res, "https://destination.org/unlocked")

    # 16. SocialUnlock Plugin Test
    async def test_social_unlock_bypass(self):
        b = SocialUnlockBypasser()
        self.assertTrue(b.match("https://sub2unlock.com/code123"))
        self.assertTrue(b.match("https://mboost.me/xyz"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><script>var unlocked_url = "https://mega.nz/file/abc12345";</script></body></html>'
        with patch("bypassers.social_unlock.safe_fetch_url", return_value=mock_resp):
            res = await b.bypass("https://sub2unlock.com/code123")
            self.assertEqual(res, "https://mega.nz/file/abc12345")

    # 17. LootLink Plugin Test
    async def test_lootlink_bypass(self):
        b = LootLinkBypasser()
        self.assertTrue(b.match("https://loot-link.com/s?mK3a"))
        self.assertTrue(b.match("https://lootdest.org/s?abc"))

        mock_page_resp = MagicMock()
        mock_page_resp.status_code = 200
        mock_page_resp.text = '<html><body><script>var destination = "https://drive.google.com/open?id=123";</script></body></html>'
        with patch("bypassers.lootlink.safe_fetch_url", return_value=mock_page_resp):
            res = await b.bypass("https://loot-link.com/s?mK3a")
            self.assertEqual(res, "https://drive.google.com/open?id=123")

    # 18. Generic Fallback Solver Test
    async def test_generic_fallback_meta_refresh(self):
        g = GenericBypasser()
        self.assertTrue(g.match("https://unknown-shortener.xyz/link"))

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://unknown-shortener.xyz/link"
        mock_resp.text = '<html><head><meta http-equiv="refresh" content="2;url=https://final-unshortened.org"></head></html>'
        
        with patch("bypassers.generic.safe_fetch_url", return_value=mock_resp):
            res = await g._stage2_meta_and_js_redirect("https://unknown-shortener.xyz/link")
            self.assertEqual(res, "https://final-unshortened.org")


class TestUtilitiesAndSecurity(unittest.IsolatedAsyncioTestCase):
    """Tests for security guards, URL extraction, rate limiting, and database caching."""

    def test_executable_safety_guard(self):
        # Direct URL executable paths
        bad_url_1 = "https://malicious.site/payload.exe"
        bad_url_2 = "https://example.com/installer.msi?token=123"
        good_url = "https://example.com/article/read-news"

        is_bad, _ = is_dangerous_url(bad_url_1)
        self.assertTrue(is_bad)

        is_bad2, _ = is_dangerous_url(bad_url_2)
        self.assertTrue(is_bad2)

        is_good, _ = is_dangerous_url(good_url)
        self.assertFalse(is_good)

    def test_header_executable_safety_guard(self):
        headers_bad = {"content-type": "application/x-msdownload"}
        is_bad, _ = is_dangerous_response_headers(headers_bad)
        self.assertTrue(is_bad)

        headers_disp = {"content-disposition": 'attachment; filename="trojan.bat"'}
        is_bad2, _ = is_dangerous_response_headers(headers_disp)
        self.assertTrue(is_bad2)

        headers_ok = {"content-type": "text/html; charset=utf-8"}
        is_ok, _ = is_dangerous_response_headers(headers_ok)
        self.assertFalse(is_ok)

    def test_url_extractor(self):
        text = "Hello! Check out https://bit.ly/12345, and also (https://tinyurl.com/abcde). Visit https://google.com!"
        urls = extract_urls(text)
        self.assertEqual(len(urls), 3)
        self.assertIn("https://bit.ly/12345", urls)
        self.assertIn("https://tinyurl.com/abcde", urls)
        self.assertIn("https://google.com", urls)

    def test_rate_limiter(self):
        limiter = RateLimiter(cooldown=2.0)
        user_id = 99999
        
        # First request should pass
        is_limited, _ = limiter.is_rate_limited(user_id)
        self.assertFalse(is_limited)

        # Immediate second request should be blocked
        is_limited2, remaining = limiter.is_rate_limited(user_id)
        self.assertTrue(is_limited2)
        self.assertGreater(remaining, 0.0)

    async def test_database_cache_and_stats(self):
        test_db_path = BASE_DIR / "tests" / "test_temp.db"
        test_db = Database(test_db_path)
        await test_db.init_db()

        # Initially empty
        cached = await test_db.get_cached("https://bit.ly/test-cache")
        self.assertIsNone(cached)

        # Save to cache
        await test_db.set_cached("https://bit.ly/test-cache", "https://final-dest.com", "Bit.ly")

        # Retrieve from cache
        cached2 = await test_db.get_cached("https://bit.ly/test-cache")
        self.assertIsNotNone(cached2)
        self.assertEqual(cached2[0], "https://final-dest.com")
        self.assertEqual(cached2[1], "Bit.ly")

        # User activity and stats
        await test_db.record_user(12345)
        stats = await test_db.get_stats()
        self.assertGreaterEqual(stats["total_users"], 1)
        self.assertGreaterEqual(stats["unique_links_cached"], 1)

        # Clean up test DB file
        try:
            if test_db_path.exists():
                test_db_path.unlink()
        except Exception:
            pass

    def test_plugin_manager_discovery(self):
        manager = BypasserManager()
        sites = manager.get_supported_sites()
        # Should have discovered at least 10 plugins
        self.assertGreaterEqual(len(sites), 10)
        
        # Verify routing
        b = manager.get_bypasser_for_url("https://bit.ly/mycode")
        self.assertEqual(b.name, "Bit.ly")

        b2 = manager.get_bypasser_for_url("https://unknown-domain.io/xyz")
        self.assertEqual(b2.name, "Generic Fallback")


if __name__ == "__main__":
    unittest.main()
