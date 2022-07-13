import itertools


def is_boss(name: str) -> bool:
    return name in boss_names


def is_play_char(name: str) -> bool:
    return name in itertools.chain.from_iterable(play_char_names.values())


boss_names = [
    "ゴブリングレート",
    "ワイバーン",
    "ワイルドグリフォン",
    "ライライ",
    "ランドスロース",
    "ライデン",
    "シードレイク",
    "バジリスク",
    "ニードルクリーパー",
    "オークチーフ",
    "スカイワルキューレ",
    "レイスロード",
    "マダムプリズム",
    "ムシュフシュ",
    "ジャッカルシーフ",
    "メガラバーン",
    "ムーバ",
    "トライロッカー",
    "スピリットホーン",
    "ティタノタートル",
    "オブシダンワイバーン",
    "ウールヴヘジン",
    "ネプテリオン",
    "ダークガーゴイル",
    "マッドベア",
    "サイクロプス",
    "アクアリオス",
    "トルペドン",
    "メサルティム",
    "ミノタウロス",
    "ツインピッグス",
    "カルキノス",
    "オルレオン",
    "メデューサ",
    "グラットン",
    "レサトパルト",
    "サジタリウス",
    "アルゲティ",
    "ソードコブラ",
]

play_char_names = {
    "ノゾミ": ["ノゾミ"],
    "ノゾミ(サマー)": ["ノゾミ(サマー)", "水ノゾ", "水ゾ"],
    "ノゾミ(クリスマス)": ["ノゾミ(クリスマス)", "クリノゾミ", "クリノゾ"],
    "ツムギ": ["ツムギ"],
    "ツムギ(サマー)": ["ツムギ(サマー)", "水ツムギ", "水ツム"],
    "ツムギ(ハロウィン)": ["ツムギ(ハロウィン)", "ハロツム", "ハロ麦"],
    "チカ": ["チカ"],
    "チカ(サマー)": ["チカ(サマー)", "水チカ", "サマチカ"],
    "チカ(クリスマス)": ["チカ(クリスマス)", "クリチカ"],
    "サレン": ["サレン"],
    "サレン(サマー)": ["サレン(サマー)", "水サ", "水サレン", "ミレン"],
    "サレン(クリスマス)": ["サレン(クリスマス)", "クリスマスサレン", "クリサレン", "クリサ", "クサレ", "クリサレ"],
    "アヤネ": ["アヤネ"],
    "アヤネ(クリスマス)": ["アヤネ(クリスマス)", "クリアヤネ", "クリネ", "クリキチ"],
    "クルミ": ["クルミ"],
    "クルミ(ステージ)": ["クルミ(ステージ)", "クルステ", "スルミ", "ステミ", "ステクルミ", "クルジ"],
    "クルミ(クリスマス)": ["クルミ(クリスマス)", "クリクルミ", "クリミ"],
    "スズメ": ["スズメ"],
    "スズメ(サマー)": ["スズメ(サマー)", "ミズメ"],
    "スズメ(ニューイヤー)": ["スズメ(ニューイヤー)", "ニュズメ", "振袖スズメ", "正月スズメ"],
    "ヒヨリ": ["ヒヨリ"],
    "ヒヨリ(サマー)": ["ヒヨリ(サマー)"],
    "ヒヨリ(ニューイヤー)": ["ヒヨリ(ニューイヤー)", "ニュヨリ"],
    "ヒヨリ(プリンセス)": ["ヒヨリ(プリンセス)", "プヨリ", "ヨン"],
    "レイ": ["レイ"],
    "レイ(サマー)": ["レイ(サマー)", "水レイ"],
    "レイ(ハロウィン)": ["レイ(ハロウィン)", "ハロレイ", "幽レイ"],
    "レイ(プリンセス)": ["レイ(プリンセス)", "プリレイ", "プレイ", "プイ"],
    "レイ(ニューイヤー)": ["レイ(ニューイヤー)", "ニュレイ"],
    "ユイ": ["ユイ", "草野"],
    "ユイ(サマー)": ["ユイ(サマー)", "草野"],
    "ユイ(プリンセス)": ["ユイ(プリンセス)", "プリユイ", "草野", "プリュイ", "プサノ"],
    "ユイ(儀装束)": ["ユイ(儀装束)", "ギュイ", "草野", "儀ユイ"],
    "ユイ(ニューイヤー)": ["ユイ(ニューイヤー)", "ニュイ", "草野", "しょうゆ"],
    "エリコ": ["エリコ"],
    "エリコ(サマー)": ["エリコ(サマー)", "水エリコ"],
    "エリコ(バレンタイン)": ["エリコ(バレンタイン)", "バレエリコ", "バリコ", "バレエリ"],
    "ルカ": ["ルカ"],
    "ルカ(サマー)": ["ルカ(サマー)", "水ルカ"],
    "ルカ(ニューイヤー)": ["ルカ(ニューイヤー)", "正月ルカ", "正ルカ"],
    "アンナ": ["アンナ"],
    "アンナ(サマー)": ["アンナ(サマー)", "水アンナ", "あωな"],
    "アンナ(パイレーツ)": ["アンナ(パイレーツ)", "アンパイ", "パンナ", "海アンナ"],
    "ナナカ": ["ナナカ"],
    "ナナカ(サマー)": ["ナナカ(サマー)", "水ナナカ"],
    "ミツキ": ["ミツキ"],
    "ミツキ(オーエド)": ["ミツキ(オーエド)", "オツキ"],
    "イノリ": ["イノリ", "水瀬"],
    "イノリ(怪盗)": ["イノリ(怪盗)", "カイノリ", "カノリ", "怪盗イノリ", "ドロリ", "伊藤"],
    "イノリ(タイムトラベル)": ["イノリ(タイムトラベル)", "イノベル", "タイノリ", "タノリ"],
    "カヤ": ["カヤ", "カヤぴぃ"],
    "カヤ(タイムトラベル)": ["カヤ(タイムトラベル)", "カヤベル"],
    "ホマレ": ["ホマレ"],
    "ウヅキ": ["ウヅキ", "しまむら", "卯月"],
    "リン(デレマス)": ["リン", "リン(デレマス)", "しぶりん", "デレリン"],
    "ミオ": ["ミオ", "ちゃんみお", "本田"],
    "アオイ": ["アオイ"],
    "アオイ(キャンプ)": ["アオイ(キャンプ)", "キャオイ", "アオキャン"],
    "アオイ(作業服)": ["アオイ(作業服)", "サギョイ", "サオイ", "作オイ"],
    "アオイ(編入生)": ["アオイ(編入生)", "ヘオイ", "編アオイ"],
    "ハツネ": ["ハツネ"],
    "ハツネ(サマー)": ["ハツネ(サマー)", "水ハツネ", "チツネ", "チアネ"],
    "ミサト": ["ミサト"],
    "ミサト(サマー)": ["ミサト(サマー)", "水ミサト"],
    "タマキ": ["タマキ"],
    "タマキ(サマー)": ["タマキ(サマー)", "水タマ", "水タマキ"],
    "タマキ(作業服)": ["タマキ(作業服)", "サマキ", "ドカタマ", "現場猫", "作タマ"],
    "アキノ": ["アキノ"],
    "アキノ(クリスマス)": ["アキノ(クリスマス)", "クリアキノ", "クリノ", "クリキノ", "クリアキ"],
    "ミフユ": ["ミフユ"],
    "ミフユ(サマー)": ["ミフユ(サマー)", "水ミフユ", "水ユ"],
    "ミフユ(作業服)": ["ミフユ(作業服)", "サフユ"],
    "ユカリ": ["ユカリ", "麦しゅわ"],
    "ユカリ(クリスマス)": ["ユカリ(クリスマス)", "クリユカリ", "栗しゅわ"],
    "ユカリ(キャンプ)": ["ユカリ(キャンプ)", "ユカリΔ", "ユカキャン", "ユーキャン", "キュカリ", "ユキャリ"],
    "リノ": ["リノ", "義妹"],
    "リノ(バレンタイン)": ["リノ(バレンタイン)", "ワリノ", "アリノ", "有野"],
    "リノ(クリスマス)": ["リノ(クリスマス)", "クリリノ", "クリノ"],
    "ラビリスタ": ["ラビリスタ", "ラビ", "ビスタ"],
    "ラビリスタ(オーバーロード)": ["ラビリスタ(オーバーロード)", "オバリスタ", "オビリスタ", "オバラビ"],
    "シズル": ["シズル", "偽姉"],
    "シズル(サマー)": ["シズル(サマー)", "水シズル", "ミズル"],
    "シズル(バレンタイン)": ["シズル(バレンタイン)", "バレシズ", "バズル"],
    "クレジッタ": ["クレジッタ", "クレジ", "ジッタ"],
    "ミミ": ["ミミ"],
    "ミミ(ハロウィン)": ["ミミ(ハロウィン)", "ハロミミ"],
    "ミソギ": ["ミソギ"],
    "ミソギ(ハロウィン)": ["ミソギ(ハロウィン)", "ハロミソ"],
    "キョウカ": ["キョウカ"],
    "キョウカ(ハロウィン)": ["キョウカ(ハロウィン)", "ハロキョ", "ハロウカ"],
    "スズナ": ["スズナ", "ヒデサイ"],
    "スズナ(サマー)": ["スズナ(サマー)", "水スズナ", "ミズナ", "水菜"],
    "スズナ(ハロウィン)": ["スズナ(ハロウィン)", "ハロナ", "ハロスズナ", "ハズナ"],
    "イオ": ["イオ"],
    "イオ(サマー)": ["イオ(サマー)", "水イオ"],
    "イオ(ノワール)": ["イオ(ノワール)", "黒イオ", "イワイオ", "闇イオ"],
    "ミサキ": ["ミサキ", "大人のレディ"],
    "ミサキ(ハロウィン)": ["ミサキ(ハロウィン)", "ハロミサキ"],
    "ミサキ(ステージ)": ["ミサキ(ステージ)", "ミサステ", "ステーキ", "ステミサ", "Mステ", "ミサジ", "ミサージ"],
    "ランファ": ["ランファ"],
    "ニノン": ["ニノン"],
    "ニノン(オーエド)": ["ニノン(オーエド)", "オノン", "シノン", "オニンニン"],
    "ニノン(ハロウィン)": ["ニノン(ハロウィン)", "ハノン", "ハロニノン"],
    "アユミ": ["アユミ"],
    "アユミ(怪盗)": ["アユミ(怪盗)", "カユミ"],
    "アユミ(ワンダー)": ["アユミ(ワンダー)", "ワユミ"],
    "モニカ": ["モニカ"],
    "モニカ(マジカル)": ["モニカ(マジカル)", "マジモニ", "ラブモニ", "モニカル", "らぶも", "モーラ"],
    "クウカ": ["クウカ"],
    "クウカ(ノワール)": ["クウカ(ノワール)", "農家", "黒クウカ"],
    "クウカ(オーエド)": ["クウカ(オーエド)", "オウカ"],
    "ユキ": ["ユキ"],
    "ユキ(オーエド)": ["ユキ(オーエド)", "オユキ", "江戸男", "江戸雪", "お雪"],
    "シノブ": ["シノブ"],
    "シノブ(パイレーツ)": ["シノブ(パイレーツ)", "シノパイ", "パイシノ", "海賊シノブ"],
    "シノブ(ハロウィン)": ["シノブ(ハロウィン)", "ハロシノ"],
    "ミヤコ": ["ミヤコ", "プリン"],
    "ミヤコ(ハロウィン)": ["ミヤコ(ハロウィン)", "ハロミヤ", "ハロミヤコ", "ハロプリ"],
    "ミヤコ(クリスマス)": ["ミヤコ(クリスマス)", "クリミヤ", "クリプリン", "クリリン", "クリミヤコ", "ヤコリ", "雪ミヤコ"],
    "ヨリ": ["ヨリ"],
    "ヨリ(エンジェル)": ["ヨリ(エンジェル)", "ヨリエル", "天ヨリ", "ヨリ天"],
    "アカリ": ["アカリ"],
    "アカリ(エンジェル)": ["アカリ(エンジェル)", "アカリエル", "天アカリ"],
    "イリヤ": ["イリヤ"],
    "イリヤ(ニューイヤー)": ["イリヤ(ニューイヤー)", "ニュリヤ", "イヤイヤ"],
    "イリヤ(クリスマス)": ["イリヤ(クリスマス)", "クリヤ", "クリイリヤ"],
    "リマ": ["リマ"],
    "リマ(シンデレラ)": ["リマ(シンデレラ)", "デレリマ", "リマンデ"],
    "マヒル": ["マヒル"],
    "マヒル(レンジャー)": ["マヒル(レンジャー)", "マヒルンジャー", "マヒレン"],
    "マヒル(クリスマス)": ["マヒル(クリスマス)", "クリマヒル"],
    "シオリ": ["シオリ"],
    "シオリ(マジカル)": ["シオリ(マジカル)", "マジシオ", "ピュオリ", "ピュアシオリ"],
    "リン": ["リン"],
    "リン(レンジャー)": ["リン(レンジャー)", "リンレン", "リンジャー"],
    "クリスティーナ": ["クリスティーナ"],
    "クリスティーナ(クリスマス)": ["クリスティーナ(クリスマス)", "クリクリス", "メリス"],
    "マツリ": ["マツリ"],
    "マツリ(ハロウィン)": ["マツリ(ハロウィン)", "ハロマツ", "ハツリ", "ハロ松"],
    "トモ": ["トモ"],
    "トモ(マジカル)": ["トモ(マジカル)", "マジトモ", "ニートモ", "ニート", "シャニトモ"],
    "ジュン": ["ジュン"],
    "ジュン(サマー)": ["ジュン(サマー)", "水ジュン"],
    "ぺコリーヌ": ["ぺコリーヌ", "ペコ", "6ペコ", "ユースティアナ"],
    "ぺコリーヌ(サマー)": ["ぺコリーヌ(サマー)", "水ペコ"],
    "ぺコリーヌ(ニューイヤー)": ["ぺコリーヌ(ニューイヤー)", "ニュペコ", "タコリーヌ", "タコ"],
    "ぺコリーヌ(オーバーロード)": [
        "ぺコリーヌ(オーバーロード)",
        "オペコ",
        "オバペコ",
        "バロペコ",
        "ヌオー",
        "オコリーヌ",
        "オコ",
    ],
    "ぺコリーヌ(プリンセス)": ["ぺコリーヌ(プリンセス)", "プリペコ"],
    "コッコロ": ["コッコロ", "6コロ"],
    "コッコロ(プリンセス)": ["コッコロ(プリンセス)", "プリコロ", "セスコ", "プッコロ", "ドッコモ"],
    "コッコロ(サマー)": ["コッコロ(サマー)", "水コロ"],
    "コッコロ(ニューイヤー)": ["コッコロ(ニューイヤー)", "ニュッコロ", "ニュコロ", "巫女ッコロ"],
    "コッコロ(儀装束)": ["コッコロ(儀装束)", "ギッコロ", "ギスコ", "儀コロ"],
    "キャル": ["キャル"],
    "キャル(サマー)": ["キャル(サマー)", "水キャル", "水野球"],
    "キャル(プリンセス)": ["キャル(プリンセス)", "プリキャル"],
    "キャル(オーバーロード)": ["キャル(オーバーロード)", "オキャル", "オバキャル", "オャル"],
    "キャル(ニューイヤー)": ["キャル(ニューイヤー)", "ニャル", "にゃる", "野球", "ニュル"],
    "シェフィ": ["シェフィ"],
    "シェフィ(ニューイヤー)": ["シェフィ(ニューイヤー)", "ニュフィ"],
    "チエル": ["チエル"],
    "チエル(聖学祭)": ["チエル(聖学祭)", "聖チエル", "祭チエル"],
    "クロエ": ["クロエ"],
    "クロエ(聖学祭)": ["クロエ(聖学祭)", "聖クロエ", "祭クロエ"],
    "ユニ": ["ユニ"],
    "ユニ(聖学祭)": ["ユニ(聖学祭)", "聖ユニ", "聖学ユニ"],
    "カオリ": ["カオリ"],
    "カオリ(ハロウィン)": ["カオリ(ハロウィン)", "ハオリ", "ハロカオリ"],
    "カオリ(サマー)": ["カオリ(サマー)", "水カオリ"],
    "マコト": ["マコト"],
    "マコト(サマー)": ["マコト(サマー)", "ミコト", "水マコト", "水マコ"],
    "マコト(シンデレラ)": ["マコト(シンデレラ)", "マンデ", "デレマコ"],
    "マホ": ["マホ"],
    "マホ(シンデレラ)": ["マホ(シンデレラ)", "デレマホ", "マホンデ"],
    "マホ(サマー)": ["マホ(サマー)", "水マホ", "水パコ", "花火"],
    "カスミ": ["カスミ"],
    "カスミ(サマー)": ["カスミ(サマー)", "サマカス", "水カス", "ミスミ"],
    "カスミ(マジカル)": ["カスミ(マジカル)", "マジカス", "マジミ", "ミスティ"],
    "ジータ": ["ジータ"],
    "アリサ": ["アリサ"],
    "レム": ["レム"],
    "ラム": ["ラム"],
    "ムイミ": ["ムイミ", "ノウェム"],
    "ムイミ(ニューイヤー)": ["ムイミ(ニューイヤー)", "ニュイミ"],
    "カリン": ["カリン", "眼鏡", "緑", "糖"],
    "ネネカ": ["ネネカ"],
    "ネネカ(ニューイヤー)": ["ネネカ(ニューイヤー)", "ニュネカ", "傘"],
    "アン": ["アン"],
    "グレア": ["グレア"],
    "ルゥ": ["ルゥ"],
    "ルナ": ["ルナ"],
    "エミリア": ["エミリア"],
    "ヴァンピィ": ["ヴァンピィ"],
    "アキノ＆サレン": ["アキノ＆サレン", "アキサレ"],
    "ハツネ＆シオリ": ["ハツネ＆シオリ", "ハツシオ"],
    "ミソギ＆ミミ＆キョウカ": ["ミソギ＆ミミ＆キョウカ", "リトリリ", "リリリ"],
}
