import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io

# ---------------------------------------------------------
# 画像処理ロジック (元のコードから移植・Web用に調整)
# ---------------------------------------------------------

def create_gradient(width, height):
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    for i in range(height):
        alpha = int(180 * (i / height))
        draw.line([(0, i), (width, i)], fill=(0, 0, 0, alpha))
    return gradient

def create_faded_line(width, height):
    line = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    mask = Image.new('L', (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    max_alpha = 204
    fade_width = max(1, int(width * 0.15)) if width > 0 else 0
    for i in range(width):
        alpha = max_alpha
        if i < fade_width: alpha = int(max_alpha * (i / fade_width))
        elif i > width - fade_width: alpha = int(max_alpha * ((width - i) / fade_width))
        draw_mask.line([(i, 0), (i, height)], fill=alpha)
    line.putalpha(mask)
    return line

def get_text_length(text, font):
    # 簡易化: Web版では複雑なフォールバックを省略し、単一フォントで計算
    return font.getlength(text)

def draw_text_with_shadow(draw, xy, text, font, text_color, shadow_enabled, shadow_offset):
    x, y = xy
    if shadow_enabled:
        shadow_color = (0, 0, 0, 180)
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=text_color)

def generate_image(image_file, font_file, name_text, main_text, 
                  name_size, text_size, show_name, shadow_enabled, 
                  shadow_offset, add_letterbox, trim_top):
    
    # 画像を開く
    base_img = Image.open(image_file).convert("RGBA")
    original_width, original_height = base_img.size

    # フォントの読み込み (Webサーバーにはフォントがないため、アップロードされたものかデフォルトを使用)
    try:
        if font_file:
            primary_name_font = ImageFont.truetype(font_file, name_size)
            primary_text_font = ImageFont.truetype(font_file, text_size)
        else:
            # フォントがない場合の非常用（日本語が出ない可能性があります）
            primary_name_font = ImageFont.load_default()
            primary_text_font = ImageFont.load_default()
    except Exception as e:
        st.error(f"フォント読み込みエラー: {e}")
        return None

    lines = main_text.split('\n')
    
    output_img, text_draw_base_y = None, 0
    
    # --- 背景・レターボックス処理 ---
    if add_letterbox:
        v_padding = text_size * 0.5
        main_text_height = text_size * 1.2 * len(lines)
        name_part_height = (name_size * 1.2) + (name_size * 0.5) if show_name else 0
        letterbox_height = int(name_part_height + main_text_height + v_padding * 2)
        
        if trim_top:
            output_img = Image.new("RGBA", (original_width, original_height), (0, 0, 0, 255))
            # はみ出す分を下からカットするために、画像を上にずらして貼り付け等はせず、
            # 元のロジックに合わせてクロップ
            crop_height = original_height - letterbox_height
            if crop_height > 0:
                img_to_paste = base_img.crop((0, letterbox_height, original_width, original_height)) # 下側を使う
                # 元コードのロジックを再現: 上を削って、下に黒帯をつけるスペースを作る
                # 元コード: base_img.crop((0, letterbox_height, original_width, original_height))
                output_img.paste(img_to_paste, (0, 0))
            else:
                 output_img.paste(base_img, (0,0)) # 画像が小さすぎる場合
            
            text_draw_base_y = original_height - letterbox_height
        else:
            output_img = Image.new("RGBA", (original_width, original_height + letterbox_height), (0, 0, 0, 255))
            output_img.paste(base_img, (0, 0))
            text_draw_base_y = original_height
    else:
        output_img = base_img.copy()
        gradient_height = int(original_height * 0.35)
        gradient = create_gradient(original_width, gradient_height)
        output_img.alpha_composite(gradient, (0, original_height - gradient_height))

    # --- テキスト描画レイヤー ---
    txt_layer = Image.new("RGBA", output_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    # 本文の描画位置計算
    line_widths = [get_text_length(line, primary_text_font) for line in lines]
    max_line_width = max(line_widths) if line_widths else 0
    text_block_start_x = (output_img.width - max_line_width) / 2
    
    if add_letterbox:
        # 元コード: letterbox_height - (text_font_size * 0.5) ...
        # 正確な移植のため、bottom_yを計算
        bottom_y = text_draw_base_y + letterbox_height - (text_size * 0.5)
        main_text_top_y = bottom_y - (text_size * 1.2 * len(lines))
    else:
        bottom_y = int(output_img.height * 0.95)
        main_text_top_y = bottom_y - (text_size * 1.2 * len(lines))

    # 本文描画
    current_y = main_text_top_y
    for line in lines:
        draw_text_with_shadow(draw, (text_block_start_x, current_y), line, primary_text_font, (255,255,255,255), shadow_enabled, shadow_offset)
        current_y += text_size * 1.2

    # キャラクター名とライン描画
    if show_name:
        name_width = get_text_length(name_text, primary_name_font)
        # 左から1/4くらいの位置
        name_start_x = int((output_img.width / 4) - (output_img.width * 0.06))
        
        line_padding = name_size * 4 
        line_width = int(name_width + line_padding)
        line_height = max(1, int(output_img.height * 0.005))
        
        # ラインの位置
        line_start_x = int(name_start_x + (name_width / 2) - (line_width / 2))
        line_y = int(main_text_top_y - (name_size * 0.5))
        name_y = int(line_y - (name_size * 1.2))
        
        # ライン描画
        line_img = create_faded_line(line_width, line_height)
        txt_layer.paste(line_img, (line_start_x, line_y), line_img)
        
        # 名前描画
        draw_text_with_shadow(draw, (name_start_x, name_y), name_text, primary_name_font, (255,255,255,255), shadow_enabled, shadow_offset)

    return Image.alpha_composite(output_img, txt_layer)


# ---------------------------------------------------------
# Streamlit UI (画面部分)
# ---------------------------------------------------------

st.set_page_config(page_title="UMA TEXT GENERATOR Web", layout="wide")

st.title("UMA TEXT GENERATOR Web Edition")
st.markdown("画像をアップロードして、テキストを入力してください。")

# サイドバー：設定系
with st.sidebar:
    st.header("設定")
    
    st.subheader("フォント設定 (必須)")
    st.info("Web上には日本語フォントがないため、お手持ちの .ttf / .otf ファイルをアップロードしてください。")
    font_file = st.file_uploader("フォントファイルを選択", type=["ttf", "otf", "ttc"])
    
    st.subheader("サイズ調整")
    name_size = st.slider("名前サイズ", 10, 150, 45)
    text_size = st.slider("本文サイズ", 10, 150, 40)
    
    st.subheader("オプション")
    show_name = st.checkbox("名前とラインを表示", value=True)
    
    shadow_enabled = st.checkbox("文字に影を付ける", value=False)
    shadow_offset = 2
    if shadow_enabled:
        shadow_offset = st.slider("影のオフセット", 1, 10, 2)
        
    add_letterbox = st.checkbox("下部に黒帯を追加", value=False)
    trim_top = False
    if add_letterbox:
        trim_top = st.checkbox("黒帯分を上からトリミング", value=False)

# メインエリア
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 素材アップロード & 入力")
    bg_file = st.file_uploader("背景画像を選択", type=["png", "jpg", "jpeg", "bmp"])
    
    name_text = st.text_input("キャラクター名", value="キャラクター名")
    main_text = st.text_area("本文", value="ここに本文を入力してください", height=150)

with col2:
    st.subheader("2. プレビュー & 保存")
    
    if bg_file is not None and font_file is not None:
        # 画像生成実行
        with st.spinner("画像を生成中..."):
            result_image = generate_image(
                bg_file, font_file, 
                name_text, main_text,
                name_size, text_size, 
                show_name, shadow_enabled, shadow_offset,
                add_letterbox, trim_top
            )
            
            if result_image:
                st.image(result_image, caption="生成結果", use_container_width=True)
                
                # ダウンロードボタン用処理
                buf = io.BytesIO()
                result_image.convert("RGB").save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="画像をダウンロード (PNG)",
                    data=byte_im,
                    file_name="uma_gen_image.png",
                    mime="image/png"
                )
    elif bg_file is None:
        st.info("👈 左側のメニューから背景画像を選択してください。")
    elif font_file is None:
        st.warning("👈 左側のサイドバーからフォントファイル(.ttfなど)をアップロードしてください。\n(日本語を表示するために必要です)")