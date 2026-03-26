import unittest

from app.indexpro_directory import (
    DirectoryManufacturer,
    parse_manufacturer_distributor_relations,
    parse_distributor_listing,
    parse_handling_manufacturers,
    parse_manufacturer_listing,
)


class IndexProDirectoryParserTests(unittest.TestCase):
    def test_parse_distributor_listing_collects_online_sales(self) -> None:
        html = """
        <div class="search_list">
          <dl>
            <dt><span class="company"><a href="/distributor/link/contact?d_web=203">アークテイク</a></span></dt>
            <dd class="contactlink">
              <ul>
                <li><a href="/distributor/location?did=203">営業拠点</a></li>
                <li><a href="/distributor/handlingmaker?did=203">取扱メーカー</a></li>
                <li><a href="/distributor/onlinesales?did=203">オンライン販売</a></li>
              </ul>
            </dd>
          </dl>
          <dl>
            <dt><span class="company"><a href="/distributor/link/contact?d_web=204">アート科学</a></span></dt>
            <dd class="contactlink">
              <ul>
                <li><a href="/distributor/location?did=204">営業拠点</a></li>
                <li><a href="/distributor/handlingmaker?did=204">取扱メーカー</a></li>
              </ul>
            </dd>
          </dl>
        </div>
        """
        rows = parse_distributor_listing(
            "https://www.indexpro.co.jp/distributor/search-distributor?initial=%E3%81%82",
            html,
            "あ",
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].did, "203")
        self.assertEqual(rows[0].location_url, "https://www.indexpro.co.jp/distributor/location?did=203")
        self.assertEqual(rows[0].online_sales_url, "https://www.indexpro.co.jp/distributor/onlinesales?did=203")
        self.assertEqual(rows[0].source_category, "オンライン販売")
        self.assertEqual(rows[1].source_category, "代理店・取扱店")

    def test_parse_handling_manufacturers_filters_navigation_noise(self) -> None:
        html = """
        <div class="handlingmaker_list">
          <dl>
            <dt>あ</dt>
            <dd>
              <ul>
                <li><a href="/CompanyLink/3301">AIメカテック</a></li>
                <li><a href="/CompanyLink/2312">Alpha &amp; Omega Semiconductor</a></li>
              </ul>
            </dd>
          </dl>
        </div>
        <ul>
          <li><a href="/distributor/search-distributor?initial=%E3%81%82">あ</a></li>
          <li><a href="/">Home</a></li>
        </ul>
        """
        names = parse_handling_manufacturers(html)
        self.assertEqual(names, ["AIメカテック", "Alpha & Omega Semiconductor"])

    def test_parse_manufacturer_listing_collects_real_names(self) -> None:
        html = """
        <div class="search_list">
          <dl>
            <dt><span class="company"><a href="/CompanyLink/18581">アドバリューシステム</a></span></dt>
            <dd>説明</dd>
            <dd><a href="/distributor/list-distributor?mcid=18581">[代理店・取扱店]</a></dd>
          </dl>
        </div>
        """
        rows = parse_manufacturer_listing(
            "https://www.indexpro.co.jp/distributor/search-maker?initial=%E3%81%82",
            html,
            "あ",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "アドバリューシステム")
        self.assertEqual(rows[0].mcid, "18581")

    def test_parse_manufacturer_distributor_relations_collects_categories(self) -> None:
        html = """
        <div class="search_results">
          <dl>
            <dt><a href="/distributor/link/contact?d_web=2211">アイニックス</a> 取扱店</dt>
            <dd><a href="/distributor/location?did=2211">営業拠点</a></dd>
          </dl>
          <dl>
            <dt><a href="/distributor/link/contact?d_web=900">日伝</a> 正規代理店</dt>
            <dd><a href="/distributor/location?did=900">営業拠点</a></dd>
          </dl>
          <dl>
            <dt><a href="/distributor/link/contact?d_web=128">TAKAGIオンラインショップ</a> オンライン</dt>
            <dd>
              <a href="/distributor/location?did=128">営業拠点</a>
              <a href="/distributor/onlinesales?did=128">オンライン販売</a>
            </dd>
          </dl>
        </div>
        """
        manufacturer = DirectoryManufacturer(
            name="東芝テック",
            initial="と",
            listing_url="https://www.indexpro.co.jp/distributor/search-maker?initial=%E3%81%A8",
            distributor_list_url="https://www.indexpro.co.jp/distributor/list-distributor?mcid=5673",
            mcid="5673",
        )
        rows = parse_manufacturer_distributor_relations(
            manufacturer.distributor_list_url,
            html,
            manufacturer,
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].manufacturer_name, "東芝テック")
        self.assertEqual(rows[0].relation_category, "取扱店")
        self.assertEqual(rows[1].relation_category, "代理店")
        self.assertEqual(rows[2].relation_category, "オンライン販売")


if __name__ == "__main__":
    unittest.main()
