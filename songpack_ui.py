"""
Song Pack UI for TOA
Two-level navigation: Song Packs -> Levels within a pack
"""

import pygame
import os
import json
import time
import re
from songpack_loader import scan_and_load_songpacks, convert_level_to_json

# Global font cache to avoid slow SysFont calls
_FONT_CACHE = {}

def get_cached_font(names, size):
    """Get or create cached font to avoid slow SysFont lookups"""
    key = (tuple(names) if isinstance(names, list) else names, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = pygame.font.SysFont(names, size)
        except:
            _FONT_CACHE[key] = pygame.font.Font(None, size)
    return _FONT_CACHE[key]

def calculate_nps_range(level_notes):
    """Calculate min-max NPS range from level notes"""
    if not level_notes:
        return None, None
    
    # Group notes by second
    notes_by_second = {}
    for note in level_notes:
        second = int(note.get('t', 0))
        notes_by_second[second] = notes_by_second.get(second, 0) + 1
    
    if not notes_by_second:
        return None, None
    
    nps_values = list(notes_by_second.values())
    return min(nps_values), max(nps_values)

def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width, returns list of lines"""
    words = text.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + word + " " if current_line else word + " "
        test_surface = font.render(test_line, True, (255, 255, 255))
        
        if test_surface.get_width() <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line.rstrip())
            current_line = word + " "
    
    if current_line:
        lines.append(current_line.rstrip())
    
    return lines if lines else [text]

def fade_transition_out(screen, game_settings, duration=0.25):
    """Quick fade out to black"""
    if not game_settings.get('fade_effects', True):
        screen.fill((0, 0, 0))
        pygame.display.flip()
        return
    
    clock = pygame.time.Clock()
    fade_surface = pygame.Surface(screen.get_size())
    fade_surface.fill((0, 0, 0))
    
    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        alpha = int(255 * (elapsed / duration))
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    
    screen.fill((0, 0, 0))
    pygame.display.flip()

def fade_transition_in(screen, content_func, game_settings, duration=0.25):
    """Quick fade in from black"""
    if not game_settings.get('fade_effects', True):
        content_func()
        pygame.display.flip()
        return
    
    clock = pygame.time.Clock()
    fade_surface = pygame.Surface(screen.get_size())
    fade_surface.fill((0, 0, 0))
    
    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        alpha = int(255 * (1 - elapsed / duration))
        
        content_func()
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)
    
    content_func()
    pygame.display.flip()


def show_songpack_selector(screen, game_settings, resource_path_func, songpacks_path=None):
    """
    Show song pack selection screen with level selector layout.
    Returns: Selected pack info or None/QUIT
    """
    import math
    
    # Load song packs
    if songpacks_path is None:
        # Default to .toa/assets/songpacks if .toa exists, otherwise assets/songpacks
        songpacks_path = os.path.join('.toa', 'assets', 'songpacks') if os.path.exists('.toa') else os.path.join('assets', 'songpacks')
    
    # Extracted songpacks go to .toa/songpacks/extracted or songpacks/extracted
    extracted_path = os.path.join('.toa', 'songpacks', 'extracted') if os.path.exists('.toa') else os.path.join('songpacks', 'extracted')
    
    packs = scan_and_load_songpacks(songpacks_path, extracted_path)
    
    if not packs:
        print("No song packs found!")
        return None
    
    # Pre-load FULL metadata cache for all packs for instant navigation
    for pack in packs:
        print(f"Pre-loading metadata for {pack['pack_name']}...")
        pack['metadata_cache'] = build_pack_metadata_cache(pack)
        
        # Pre-build COMPLETE level_metadata list for instant loading
        pack['level_metadata_full'] = []
        for json_path, meta in pack['metadata_cache'].items():
            # Calculate BPM text
            bpm_min = meta['bpm_min']
            bpm_max = meta['bpm_max']
            if bpm_min is not None and bpm_max is not None:
                if bpm_min == bpm_max:
                    bpm_text = f"{int(bpm_min)}"
                else:
                    bpm_text = f"{int(bpm_min)}-{int(bpm_max)}"
            else:
                bpm_text = "Unknown"
            
            # Get NPS range
            nps_min = meta.get('nps_min')
            nps_max = meta.get('nps_max')
            if nps_min is not None and nps_max is not None:
                if nps_min == nps_max:
                    nps_text = f"{nps_min}"
                else:
                    nps_text = f"{nps_min}-{nps_max}"
            else:
                nps_text = "Unknown"
            
            pack['level_metadata_full'].append((
                json_path,
                meta['title'],
                meta['version'],
                meta['artist'],
                meta['creator'],
                meta.get('thumbnail_file') or meta['background_file'],  # Use bn.* thumbnail for level box, fallback to bg.*
                meta['note_count'],
                bpm_text,
                nps_text,
                meta.get('length')
            ))
        
        # Keep simple list for backward compatibility
        pack['level_metadata'] = []
        for json_path, meta in pack['metadata_cache'].items():
            pack['level_metadata'].append({
                'title': meta['title'],
                'artist': meta['artist'],
                'version': meta['version'],
                'json_path': json_path
            })
    
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    # Use cached fonts for instant loading
    font_title = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 48)
    font_pack_name = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 32)
    font_stats = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 22)
    font_hint = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 24)
    font_level_name = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 20)
    
    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    GREEN = (112, 255, 148)
    
    # Layout: Left 40% for pack boxes, Right 60% for info
    list_width = int(window_width * 0.4)
    info_panel_x = list_width + 50
    
    # Scrolling setup
    scroll_offset = 0.0
    item_height = 60  # Same as level selector
    list_start_y = 80
    list_end_y = window_height - 50
    available_height = list_end_y - list_start_y
    total_content_height = len(packs) * item_height
    max_scroll = max(0.0, total_content_height - available_height)
    scroll_speed = game_settings.get('scroll_speed', 75)
    
    # Mouse drag tracking
    mouse_down_pos = None
    mouse_down_y = 0
    item_dragging = False
    
    # Hover animation
    hover_animation = {}
    
    # Drop-down animation for pack bars
    drop_animation_time = 0.0
    drop_animation_duration = 1.2  # Slower animation for better visibility

    hovered_index = None
    selected_pack = None
    
    while selected_pack is None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - scroll_speed)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + scroll_speed)
            
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset = max(0, min(max_scroll, scroll_offset - event.y * scroll_speed))
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if mouse_pos[0] < list_width:
                    mouse_down_pos = mouse_pos
                    mouse_down_y = mouse_pos[1]
                    item_dragging = False
                else:
                    mouse_down_pos = None
            
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if mouse_down_pos is not None and not item_dragging:
                    drag_distance = abs(mouse_pos[1] - mouse_down_y)
                    if drag_distance < 5 and hovered_index is not None:
                        selected_pack = packs[hovered_index]
                mouse_down_pos = None
                item_dragging = False
        
        # If a pack was selected, return immediately
        if selected_pack is not None:
            return selected_pack
        
        # Handle continuous arrow key scrolling
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            scroll_offset = max(0, scroll_offset - scroll_speed / 6)
        if keys[pygame.K_DOWN]:
            scroll_offset = min(max_scroll, scroll_offset + scroll_speed / 6)
        
        # Handle item drag scrolling
        if mouse_down_pos is not None:
            drag_delta_y = mouse_pos[1] - mouse_down_y
            if abs(drag_delta_y) > 5:
                item_dragging = True
                scroll_offset = max(0, min(max_scroll, scroll_offset - drag_delta_y * 2))
                mouse_down_y = mouse_pos[1]
        
        # Update drop animation timer
        if drop_animation_time < drop_animation_duration:
            drop_animation_time += 1.0 / 60.0  # Assuming 60 FPS
        
        # Draw
        screen.fill(BLACK)
        
        # Title - positioned on the right side
        title_text = font_title.render("Select Song Pack", True, WHITE)
        title_rect = title_text.get_rect(midtop=(info_panel_x + (window_width - info_panel_x) // 2, 30))
        screen.blit(title_text, title_rect)
        
        # Hint - positioned on the right side at bottom
        hint_text = font_hint.render("ESC: Back  |  Scroll: Navigate", True, GRAY)
        hint_rect = hint_text.get_rect(midright=(window_width - 30, window_height - 30))
        screen.blit(hint_text, hint_rect)
        
        # Update hover animations
        for idx in list(hover_animation.keys()):
            if idx == hovered_index:
                hover_animation[idx] = min(1.0, hover_animation[idx] + 0.22)
            else:
                hover_animation[idx] = max(0.0, hover_animation[idx] - 0.22)
                if hover_animation[idx] <= 0:
                    del hover_animation[idx]
        
        # Draw pack list
        hovered_index = None
        
        for idx, pack in enumerate(packs):
            # All items drop together (no stagger)
            y_pos = list_start_y + idx * item_height - int(scroll_offset)
            
            item_progress = max(0.0, min(1.0, drop_animation_time / 0.8))  # 0.8s duration
            
            # Apply easeOutQuint for smooth deceleration
            t = item_progress
            item_eased = 1 - pow(1 - t, 5)  # Quintic ease-out
            
            drop_offset = int((1.0 - item_eased) * -300)  # Start 300px above
            y_pos += drop_offset
            
            # Only skip if completely off screen AND animation is complete
            if item_progress >= 1.0 and (y_pos + item_height < list_start_y or y_pos > list_end_y):
                continue
            
            # Skip rendering if item is still animating but would be below visible area
            # This prevents pile-up at the bottom
            if y_pos > list_end_y:
                continue
            
            # Base item rect
            base_width = list_width - 40
            base_height = item_height
            base_x = 20
            item_rect = pygame.Rect(base_x, y_pos, base_width, base_height)
            
            # Check hover (but not during drag)
            is_hovered = False
            if not item_dragging and item_rect.collidepoint(mouse_pos) and mouse_pos[0] < list_width + 30:
                is_hovered = True
                hovered_index = idx
                if idx not in hover_animation:
                    hover_animation[idx] = 0.0
            
            # Apply hover animation
            if idx in hover_animation and hover_animation[idx] > 0:
                t = hover_animation[idx]
                eased_t = 1 - pow(1 - t, 3)
                shift_amount = int(30 * eased_t)
                height_shrink = int(5 * eased_t)
                shrunk_height = base_height - height_shrink
                item_rect = pygame.Rect(base_x + shift_amount, y_pos + height_shrink // 2, base_width, shrunk_height)
            
            # Draw background with cover scaling
            if pack['pack_image'] and os.path.exists(pack['pack_image']):
                try:
                    img = pygame.image.load(pack['pack_image'])
                    img_width, img_height = img.get_size()
                    scale_x = item_rect.width / img_width
                    scale_y = item_rect.height / img_height
                    scale = max(scale_x, scale_y)
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    img_scaled = pygame.transform.scale(img, (new_width, new_height))
                    img_x = item_rect.x + (item_rect.width - new_width) // 2
                    img_y = item_rect.y + (item_rect.height - new_height) // 2
                    
                    clip_region = screen.get_clip()
                    screen.set_clip(item_rect)
                    screen.blit(img_scaled, (img_x, img_y))
                    screen.set_clip(clip_region)
                    
                    # Dark overlay for text readability
                    overlay = pygame.Surface((item_rect.width, item_rect.height))
                    overlay.set_alpha(170)  # Darker overlay
                    overlay.fill(BLACK)
                    screen.blit(overlay, item_rect)
                except:
                    pygame.draw.rect(screen, BLACK, item_rect)
            else:
                pygame.draw.rect(screen, BLACK, item_rect)
            
            # Border
            border_color = GREEN if is_hovered else WHITE
            pygame.draw.rect(screen, border_color, item_rect, 1)
            
            # Pack name, centered vertically
            pack_name_str = pack['pack_name']
            max_name_width = item_rect.width - 40
            pack_name_surface = font_pack_name.render(pack_name_str, True, WHITE)
            
            # Truncate if too long
            while pack_name_surface.get_width() > max_name_width and len(pack_name_str) > 3:
                pack_name_str = pack_name_str[:-1]
                pack_name_surface = font_pack_name.render(pack_name_str + "...", True, WHITE)
            
            if len(pack_name_str) < len(pack['pack_name']) and not pack_name_str.endswith("..."):
                pack_name_str += "..."
                pack_name_surface = font_pack_name.render(pack_name_str, True, WHITE)
            
            name_y = item_rect.y + (item_rect.height - pack_name_surface.get_height()) // 2
            screen.blit(pack_name_surface, (item_rect.x + 20, name_y))
        
        # Draw info panel for hovered pack
        if hovered_index is not None and hovered_index < len(packs):
            pack = packs[hovered_index]
            
            # Info panel background
            info_panel_rect = pygame.Rect(info_panel_x, 120, window_width - info_panel_x - 50, window_height - 200)
            info_bg = pygame.Surface((info_panel_rect.width, info_panel_rect.height))
            info_bg.set_alpha(30)
            info_bg.fill(WHITE)
            screen.blit(info_bg, info_panel_rect)
            pygame.draw.rect(screen, GRAY, info_panel_rect, 2)
            
            # Display pack info
            info_y = info_panel_rect.y + 20
            info_x = info_panel_rect.x + 20
            max_text_width = info_panel_rect.width - 40
            
            # Pack name
            name_lines = wrap_text(pack['pack_name'], font_pack_name, max_text_width)
            for line in name_lines:
                name_surface = font_pack_name.render(line, True, WHITE)
                screen.blit(name_surface, (info_x, info_y))
                info_y += 40
            info_y += 10
            
            # Pack stats - total songs
            level_metadata = pack.get('level_metadata', [])
            num_songs = len(level_metadata)
            stats_text = f"Total: {num_songs} songs"
            stats_surface = font_stats.render(stats_text, True, GREEN)
            screen.blit(stats_surface, (info_x, info_y))
            info_y += 30
            
            # Difficulty breakdown
            difficulty_counts = {}
            for level_meta in level_metadata:
                version = level_meta['version'].lower()
                if 'easy' in version or 'beginner' in version:
                    difficulty_counts['Easy'] = difficulty_counts.get('Easy', 0) + 1
                elif 'medium' in version or 'platter' in version:
                    difficulty_counts['Medium'] = difficulty_counts.get('Medium', 0) + 1
                elif 'normal' in version or 'basic' in version:
                    difficulty_counts['Normal'] = difficulty_counts.get('Normal', 0) + 1
                elif 'hard' in version or 'advanced' in version:
                    difficulty_counts['Hard'] = difficulty_counts.get('Hard', 0) + 1
                elif 'expert' in version or 'insane' in version:
                    difficulty_counts['Expert'] = difficulty_counts.get('Expert', 0) + 1
                elif 'extra' in version or 'challenge' in version or 'master' in version:
                    difficulty_counts['Challenge'] = difficulty_counts.get('Challenge', 0) + 1
            
            # Display difficulty breakdown with stars
            difficulty_order = ['Easy', 'Medium', 'Normal', 'Hard', 'Expert', 'Challenge']
            difficulty_colors = {
                'Easy': (100, 200, 255),
                'Medium': (150, 220, 150),
                'Normal': (100, 255, 100),
                'Hard': (255, 200, 100),
                'Expert': (255, 100, 100),
                'Challenge': (200, 100, 255)
            }
            
            for diff_name in difficulty_order:
                if diff_name in difficulty_counts:
                    count = difficulty_counts[diff_name]
                    diff_color = difficulty_colors[diff_name]
                    
                    # Draw star
                    star_size = 12
                    star_x = info_x + 10
                    star_y = info_y + 10
                    star_points = []
                    for i in range(10):
                        angle = math.pi / 2 + (2 * math.pi * i / 10)
                        radius = star_size // 2 if i % 2 == 0 else star_size // 4
                        px = star_x + int(radius * math.cos(angle))
                        py = star_y - int(radius * math.sin(angle))
                        star_points.append((px, py))
                    pygame.draw.polygon(screen, diff_color, star_points)
                    
                    # Difficulty text
                    diff_text = f"{diff_name}: {count}"
                    diff_surface = font_level_name.render(diff_text, True, diff_color)
                    screen.blit(diff_surface, (star_x + star_size + 10, info_y))
                    info_y += 25
            
            info_y += 15
            
            # Show limited level list (max 8 levels)
            max_levels_to_show = 8
            if level_metadata:
                levels_text = font_stats.render("Songs:", True, WHITE)
                screen.blit(levels_text, (info_x, info_y))
                info_y += 30
                
                for idx, level_meta in enumerate(level_metadata[:max_levels_to_show]):
                    # Get difficulty color
                    version = level_meta['version']
                    version_lower = version.lower()
                    if 'easy' in version_lower or 'beginner' in version_lower:
                        difficulty_color = (100, 200, 255)
                    elif 'medium' in version_lower or 'platter' in version_lower:
                        difficulty_color = (150, 220, 150)
                    elif 'normal' in version_lower or 'basic' in version_lower:
                        difficulty_color = (100, 255, 100)
                    elif 'hard' in version_lower or 'advanced' in version_lower:
                        difficulty_color = (255, 200, 100)
                    elif 'expert' in version_lower or 'insane' in version_lower:
                        difficulty_color = (255, 100, 100)
                    elif 'extra' in version_lower or 'challenge' in version_lower or 'master' in version_lower:
                        difficulty_color = (200, 100, 255)
                    else:
                        difficulty_color = (200, 200, 200)
                    
                    # Draw small star
                    star_size = 10
                    star_x = info_x + 8
                    star_y = info_y + 8
                    star_points = []
                    for i in range(10):
                        angle = math.pi / 2 + (2 * math.pi * i / 10)
                        radius = star_size // 2 if i % 2 == 0 else star_size // 4
                        px = star_x + int(radius * math.cos(angle))
                        py = star_y - int(radius * math.sin(angle))
                        star_points.append((px, py))
                    pygame.draw.polygon(screen, difficulty_color, star_points)
                    
                    # Level title (truncated)
                    level_title = level_meta['title'][:25]
                    level_text = f"{level_title} [{version[:10]}]"
                    level_surface = font_level_name.render(level_text, True, difficulty_color)
                    screen.blit(level_surface, (star_x + star_size + 8, info_y))
                    info_y += 22
                
                # Show "and X more" if there are more songs
                remaining = len(level_metadata) - max_levels_to_show
                if remaining > 0:
                    more_text = f"... and {remaining} more songs"
                    more_surface = font_level_name.render(more_text, True, GRAY)
                    screen.blit(more_surface, (info_x + 8, info_y))
                    info_y += 25
            
            # Draw pack image at bottom if available
            if pack['pack_image'] and os.path.exists(pack['pack_image']):
                try:
                    # Calculate available space for image
                    available_height = info_panel_rect.y + info_panel_rect.height - info_y - 20
                    if available_height > 80:  # Only show if enough space
                        img = pygame.image.load(pack['pack_image'])
                        img_width, img_height = img.get_size()
                        
                        # Scale to fit width and available height
                        max_img_width = info_panel_rect.width - 40
                        max_img_height = min(150, available_height)
                        
                        scale_x = max_img_width / img_width
                        scale_y = max_img_height / img_height
                        scale = min(scale_x, scale_y)
                        
                        new_width = int(img_width * scale)
                        new_height = int(img_height * scale)
                        img_scaled = pygame.transform.scale(img, (new_width, new_height))
                        
                        # Center horizontally, position at bottom
                        img_x = info_panel_rect.x + (info_panel_rect.width - new_width) // 2
                        img_y = info_panel_rect.y + info_panel_rect.height - new_height - 15
                        
                        screen.blit(img_scaled, (img_x, img_y))
                except:
                    pass
        
        pygame.display.flip()
        clock.tick(60)


def build_pack_metadata_cache(pack_info):
    """Build metadata cache for all levels in a pack"""
    metadata_cache = {}
    seen_jsons = set()
    
    # Get all JSON files in levels directory
    all_level_files = set()
    if os.path.exists('levels'):
        all_level_files = set(os.listdir('levels'))
    
    for level_info in pack_info['levels']:
        folder_name = level_info['name']
        safe_pattern = re.sub(r'[^\w\s-]', '', folder_name).strip().replace(' ', '_')
        
        # Find matching JSON files
        for file in all_level_files:
            if file.lower().endswith('.json'):
                json_name_base = os.path.splitext(file)[0]
                if safe_pattern.lower() in json_name_base.lower():
                    full_path = os.path.join('levels', file)
                    if full_path not in seen_jsons:
                        seen_jsons.add(full_path)
                        
                        # Load metadata
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                meta = data.get('meta', {})
                                level_notes = data.get('level', [])
                                
                                nps_min, nps_max = calculate_nps_range(level_notes)
                                
                                # Get thumbnail file - check JSON first, then search for bn.* file
                                thumbnail_file = meta.get('thumbnail_file')
                                if not thumbnail_file:
                                    # Look for bn.* file in the same directory as background
                                    bg_file = meta.get('background_file')
                                    if bg_file and os.path.exists(bg_file):
                                        bg_dir = os.path.dirname(bg_file)
                                        for ext in ['.png', '.jpg', '.jpeg']:
                                            bn_path = os.path.join(bg_dir, f'bn{ext}')
                                            if os.path.exists(bn_path):
                                                thumbnail_file = bn_path
                                                break
                                
                                metadata_cache[full_path] = {
                                    'title': meta.get('title', 'Unknown'),
                                    'version': meta.get('version', 'Unknown'),
                                    'artist': meta.get('artist', 'Unknown'),
                                    'creator': meta.get('creator', 'Unknown'),
                                    'note_count': len(level_notes),
                                    'bpm_min': meta.get('bpm_min'),
                                    'bpm_max': meta.get('bpm_max'),
                                    'background_file': meta.get('background_file'),  # bg.* for in-game
                                    'thumbnail_file': thumbnail_file,  # bn.* for level boxes
                                    'length': meta.get('length'),
                                    'nps_min': nps_min,
                                    'nps_max': nps_max
                                }
                        except Exception as e:
                            print(f"Error caching {full_path}: {e}")
    
    return metadata_cache


def show_pack_levels_selector(screen, pack_info, game_settings, resource_path_func, metadata_cache=None):
    """
    Show levels within a selected song pack.
    Returns: Path to selected level JSON or None/QUIT
    metadata_cache: Optional pre-loaded metadata to avoid re-parsing JSONs
    """
    # Show immediate loading screen with rotating dot
    window_width, window_height = screen.get_size()
    screen.fill((0, 0, 0))
    
    # Simple loading animation
    loading_font = get_cached_font(['arial'], 48)
    loading_text = loading_font.render("Loading...", True, (255, 255, 255))
    text_rect = loading_text.get_rect(center=(window_width // 2, window_height // 2))
    screen.blit(loading_text, text_rect)
    
    pygame.display.flip()
    
    # Get screen dimensions and setup fonts first
    window_width, window_height = screen.get_size()
    
    # Use cached fonts for instant loading
    font_title = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 48)
    font_item_version = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 22)
    font_hint = get_cached_font(['meiryo', 'msgothic', 'yugothic', 'arial'], 24)
    
    # Colors
    WHITE = (255, 255, 255)
    GRAY = (200, 200, 200)
    BLACK = (0, 0, 0)
    
    # Calculate layout
    list_width = int(window_width * 0.4)
    info_panel_x = list_width + 50
    
    # If pre-built level_metadata_full is available, use it directly (instant!)
    if 'level_metadata_full' in pack_info and pack_info['level_metadata_full']:
        level_metadata = pack_info['level_metadata_full']
    elif metadata_cache:
        # Use pre-loaded metadata directly
        level_jsons = list(metadata_cache.keys())
        if not level_jsons:
            print("No levels in metadata cache!")
            return None
        
        # Build level_metadata from cache
        level_metadata = []
        for json_path in level_jsons:
            cached = metadata_cache[json_path]
            
            # Calculate BPM text
            bpm_min = cached['bpm_min']
            bpm_max = cached['bpm_max']
            if bpm_min is not None and bpm_max is not None:
                if bpm_min == bpm_max:
                    bpm_text = f"{int(bpm_min)}"
                else:
                    bpm_text = f"{int(bpm_min)}-{int(bpm_max)}"
            else:
                bpm_text = "Unknown"
            
            # Get NPS range from cache
            nps_min = cached.get('nps_min')
            nps_max = cached.get('nps_max')
            if nps_min is not None and nps_max is not None:
                if nps_min == nps_max:
                    nps_text = f"{nps_min}"
                else:
                    nps_text = f"{nps_min}-{nps_max}"
            else:
                nps_text = "Unknown"
            
            # Store bg_path instead of loading image (load lazily during render)
            # Use thumbnail for level boxes, fallback to background
            thumbnail_path = cached.get('thumbnail_file') or cached['background_file']
            
            level_metadata.append((
                json_path,
                cached['title'],
                cached['version'],
                cached['artist'],
                cached['creator'],
                thumbnail_path,  # Use bn.* for level boxes, fallback to bg.*
                cached['note_count'],
                bpm_text,
                nps_text,
                cached.get('length')
            ))
    else:
        # Show loading screen since we need to do conversion/loading
        screen.fill(BLACK)
        loading_text = font_title.render("Loading...", True, WHITE)
        loading_rect = loading_text.get_rect(center=(window_width // 2, window_height // 2))
        screen.blit(loading_text, loading_rect)
        pygame.display.flip()
    
        # Convert all levels in the pack to JSON if not already done
        level_jsons = []
        seen_jsons = set()  # Track to prevent duplicates
        
        # Get all JSON files in levels directory once
        all_level_files = set()
        if os.path.exists('levels'):
            all_level_files = set(os.listdir('levels'))
        
        for level_info in pack_info['levels']:
            # Check if JSON already exists using pattern matching
            folder_name = level_info['name']
            # Remove special characters and spaces for matching
            safe_pattern = re.sub(r'[^\w\s-]', '', folder_name).strip().replace(' ', '_')
            
            # Look for existing JSONs for this level
            existing_jsons = []
            for file in all_level_files:
                if file.lower().endswith('.json'):
                    json_name_base = os.path.splitext(file)[0]
                    # Check if safe_pattern is in the filename
                    if safe_pattern.lower() in json_name_base.lower():
                        full_path = os.path.join('levels', file)
                        if full_path not in seen_jsons:  # Only add if not seen
                            existing_jsons.append(full_path)
                            seen_jsons.add(full_path)
            
            # If no JSONs exist, convert the level
            if not existing_jsons:
                print(f"Converting {level_info['name']}...")
                created = convert_level_to_json(level_info)
                for created_path in created:
                    if created_path not in seen_jsons:
                        level_jsons.append(created_path)
                        seen_jsons.add(created_path)
                # Add newly created files to all_level_files for next iteration
                for created_path in created:
                    all_level_files.add(os.path.basename(created_path))
            else:
                level_jsons.extend(existing_jsons)
        
        if not level_jsons:
            print("No levels could be loaded from this pack!")
            return None
        
        # Load metadata for each level
        level_metadata = []
        for json_path in level_jsons:
            try:
                # Load from JSON file
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    meta = data.get('meta', {})
                    level_notes = data.get('level', [])
                    
                    title = meta.get('title', 'Unknown')
                    version = meta.get('version', 'Unknown')
                    artist = meta.get('artist', 'Unknown')
                    creator = meta.get('creator', 'Unknown')
                    bg_path = meta.get('background_file')
                    
                    # Calculate statistics
                    note_count = len(level_notes)
                    
                    # Get BPM from metadata
                    bpm_min = meta.get('bpm_min')
                    bpm_max = meta.get('bpm_max')
                    if bpm_min is not None and bpm_max is not None:
                        if bpm_min == bpm_max:
                            bpm_text = f"{int(bpm_min)}"
                        else:
                            bpm_text = f"{int(bpm_min)}-{int(bpm_max)}"
                    else:
                        bpm_text = "Unknown"
                    
                    length = meta.get('length')
                    
                    # Calculate NPS range
                    nps_min, nps_max = calculate_nps_range(level_notes)
                    if nps_min is not None and nps_max is not None:
                        if nps_min == nps_max:
                            nps_text = f"{nps_min}"
                        else:
                            nps_text = f"{nps_min}-{nps_max}"
                    else:
                        nps_text = "Unknown"
                
                # Store bg_path instead of loading image (load lazily during render)
                # bg_path is already defined above
                
                level_metadata.append((json_path, title, version, artist, creator, bg_path, note_count, bpm_text, nps_text, length))
            except Exception as e:
                print(f"Error loading {json_path}: {e}")
    
    # Validation and sorting (applies to both cached and non-cached paths)
    
    if not level_metadata:
        print("No valid levels found!")
        return None
    
    # Sort levels by difficulty, then BPM, then NPM, then length
    def get_difficulty_order(version_str):
        version_lower = version_str.lower()
        if 'easy' in version_lower or 'beginner' in version_lower:
            return 0
        elif 'medium' in version_lower or 'platter' in version_lower:
            return 1
        elif 'normal' in version_lower or 'basic' in version_lower:
            return 2
        elif 'hard' in version_lower or 'advanced' in version_lower:
            return 3
        elif 'expert' in version_lower or 'insane' in version_lower:
            return 4
        elif 'extra' in version_lower or 'challenge' in version_lower or 'master' in version_lower:
            return 5
        else:
            return 6  # Unknown difficulties go last
    
    def parse_numeric_value(text):
        """Extract numeric value from strings like '175 BPM' or '3.52 NPM' or '2:45'"""
        if text is None:
            return 0
        # For length (format: "2:45"), convert to seconds
        if ':' in str(text):
            try:
                parts = str(text).split(':')
                return int(parts[0]) * 60 + int(parts[1])
            except:
                return 0
        # For BPM/NPM, extract the number
        try:
            return float(str(text).split()[0])
        except:
            return 0
    
    # Multi-key sort: difficulty (x[2]), BPM (x[7]), NPM (x[8]), length (x[9])
    level_metadata.sort(key=lambda x: (
        get_difficulty_order(x[2]),  # Primary: difficulty
        parse_numeric_value(x[7]),   # Secondary: BPM
        parse_numeric_value(x[8]),   # Tertiary: NPM
        parse_numeric_value(x[9])    # Quaternary: length
    ))
    
    # Use the standard level selector UI (simplified version)
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    # Fonts - try to use system font with CJK support for Japanese/Chinese/Korean characters
    try:
        # Try fonts with good Unicode/CJK support (Windows fonts)
        font_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'arial'], 48)
        font_item_title = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'arial'], 32)
        font_item_version = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'arial'], 22)
        font_hint = pygame.font.SysFont(['meiryo', 'msgothic', 'yugothic', 'arial'], 24)
    except:
        font_title = pygame.font.Font(None, 48)
        font_item_title = pygame.font.Font(None, 32)
        font_item_version = pygame.font.Font(None, 22)
        font_hint = pygame.font.Font(None, 24)
    
    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    BLUE = (100, 150, 255)
    GREEN = (112, 255, 148)
    
    # Layout: Left 40% for level boxes, Right 60% for info
    list_width = int(window_width * 0.4)
    info_panel_x = list_width + 50
    
    # Scrolling setup
    scroll_offset = 0.0
    item_height = 60  # Thinner tiles
    list_start_y = 80
    list_end_y = window_height - 50
    available_height = list_end_y - list_start_y
    total_content_height = len(level_metadata) * item_height
    max_scroll = max(0.0, total_content_height - available_height)
    scroll_speed = game_settings.get('scroll_speed', 75)
    
    # Mouse drag tracking
    mouse_down_pos = None
    mouse_down_y = 0
    item_dragging = False
    
    # Hover animation
    hover_animation = {}  # {idx: scale_progress}
    
    # Drop-down animation for level bars
    drop_animation_time = 0.0
    drop_animation_duration = 1.2  # Slower animation for better visibility
    
    # Image cache for lazy loading
    image_cache = {}  # {path: pygame.Surface}

    hovered_index = None
    selected_level = None
    
    while selected_level is None:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None  # Go back to pack selector
                elif event.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - scroll_speed)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + scroll_speed)
            
            if event.type == pygame.MOUSEWHEEL:
                scroll_offset = max(0, min(max_scroll, scroll_offset - event.y * scroll_speed))
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                viewport_rect = pygame.Rect(0, list_start_y, window_width, available_height)
                if viewport_rect.collidepoint(mouse_pos):
                    mouse_down_pos = mouse_pos
                    mouse_down_y = mouse_pos[1]
                    item_dragging = False
                else:
                    mouse_down_pos = None
            
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if mouse_down_pos is not None and not item_dragging:
                    drag_distance = abs(mouse_pos[1] - mouse_down_y)
                    if drag_distance < 5 and hovered_index is not None:
                        selected_level = level_metadata[hovered_index][0]
                        # Don't fade here - the game has its own fade-in
                mouse_down_pos = None
                item_dragging = False
        
        # Handle continuous arrow key scrolling
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            scroll_offset = max(0, scroll_offset - scroll_speed / 6)
        if keys[pygame.K_DOWN]:
            scroll_offset = min(max_scroll, scroll_offset + scroll_speed / 6)
        
        # Handle item drag scrolling
        if mouse_down_pos is not None:
            drag_delta_y = mouse_pos[1] - mouse_down_y
            if abs(drag_delta_y) > 5:
                item_dragging = True
                scroll_offset = max(0, min(max_scroll, scroll_offset - drag_delta_y * 2))
                mouse_down_y = mouse_pos[1]
        
        # Update drop animation timer
        if drop_animation_time < drop_animation_duration:
            drop_animation_time += 1.0 / 60.0  # Assuming 60 FPS
        
        # Draw
        screen.fill(BLACK)
        
        # Title - positioned on the right side
        title_text = font_title.render("Select Level", True, WHITE)
        title_rect = title_text.get_rect(midtop=(info_panel_x + (window_width - info_panel_x) // 2, 30))
        screen.blit(title_text, title_rect)
        
        subtitle_text = font_item_version.render(f"{pack_info['pack_name']}", True, GRAY)
        subtitle_rect = subtitle_text.get_rect(midtop=(info_panel_x + (window_width - info_panel_x) // 2, 80))
        screen.blit(subtitle_text, subtitle_rect)
        
        # Hint - positioned on the right side at bottom
        hint_text = font_hint.render("ESC: Back  |  Scroll: Navigate", True, GRAY)
        hint_rect = hint_text.get_rect(midright=(window_width - 30, window_height - 30))
        screen.blit(hint_text, hint_rect)
        
        # Update hover animations
        for idx in list(hover_animation.keys()):
            if idx == hovered_index:
                hover_animation[idx] = min(1.0, hover_animation[idx] + 0.22)
            else:
                hover_animation[idx] = max(0.0, hover_animation[idx] - 0.22)
                if hover_animation[idx] <= 0:
                    del hover_animation[idx]
        
        # Draw level list
        hovered_index = None
        
        for idx, (json_path, title, version, artist, creator, bg_path, note_count, bpm_text, nps_text, length) in enumerate(level_metadata):
            # All items drop together (no stagger)
            y_pos = list_start_y + idx * item_height - int(scroll_offset)
            
            item_progress = max(0.0, min(1.0, drop_animation_time / 0.8))  # 0.8s duration
            
            # Apply easeOutQuint for smooth deceleration
            t = item_progress
            item_eased = 1 - pow(1 - t, 5)  # Quintic ease-out
            
            drop_offset = int((1.0 - item_eased) * -300)  # Start 300px above
            y_pos += drop_offset
            
            # Only skip if completely off screen AND animation is complete
            if item_progress >= 1.0 and (y_pos + item_height < list_start_y or y_pos > list_end_y):
                continue
            
            # Skip rendering if item is still animating but would be below visible area
            # This prevents pile-up at the bottom
            if y_pos > list_end_y:
                continue
            
            # Base item rect
            base_width = list_width - 40  # Longer base width
            base_height = item_height  # No spacing
            base_x = 20
            item_rect = pygame.Rect(base_x, y_pos, base_width, base_height)
            
            # Check hover (but not during drag) - only check if mouse is within list area horizontally
            is_hovered = False
            if not item_dragging and item_rect.collidepoint(mouse_pos) and mouse_pos[0] < list_width + 30:
                is_hovered = True
                hovered_index = idx
                if idx not in hover_animation:
                    hover_animation[idx] = 0.0
            
            # Apply hover animation (move box to the right and shrink height with cubic bezier easing)
            if idx in hover_animation and hover_animation[idx] > 0:
                # Cubic bezier ease-out: smooth deceleration
                t = hover_animation[idx]
                eased_t = 1 - pow(1 - t, 3)  # ease-out cubic
                shift_amount = int(30 * eased_t)  # Up to 30px shift right
                height_shrink = int(5 * eased_t)  # Shrink up to 5px in height
                # Move entire box to the right and shrink height, center vertically
                shrunk_height = base_height - height_shrink
                item_rect = pygame.Rect(base_x + shift_amount, y_pos + height_shrink // 2, base_width, shrunk_height)
            
            # Lazy load background image if needed
            bg_image = None
            if bg_path:
                if bg_path in image_cache:
                    bg_image = image_cache[bg_path]
                elif os.path.exists(bg_path):
                    try:
                        bg_image = pygame.image.load(bg_path)
                        image_cache[bg_path] = bg_image
                    except:
                        pass
            
            # Draw background with cover scaling (like CSS background-size: cover)
            if bg_image:
                try:
                    bg_width, bg_height = bg_image.get_size()
                    # Scale to cover the entire item while maintaining aspect ratio
                    scale_x = item_rect.width / bg_width
                    scale_y = item_rect.height / bg_height
                    scale = max(scale_x, scale_y)  # Use max to cover, not min
                    new_width = int(bg_width * scale)
                    new_height = int(bg_height * scale)
                    bg_scaled = pygame.transform.scale(bg_image, (new_width, new_height))
                    # Center the image (it will overflow and be clipped)
                    bg_x = item_rect.x + (item_rect.width - new_width) // 2
                    bg_y = item_rect.y + (item_rect.height - new_height) // 2
                    
                    # Clip to item rect
                    clip_region = screen.get_clip()
                    screen.set_clip(item_rect)
                    screen.blit(bg_scaled, (bg_x, bg_y))
                    screen.set_clip(clip_region)
                    
                    # Dark overlay for text readability
                    overlay = pygame.Surface((item_rect.width, item_rect.height))
                    overlay.set_alpha(170)  # Darker overlay
                    overlay.fill(BLACK)
                    screen.blit(overlay, item_rect)
                except:
                    pygame.draw.rect(screen, BLACK, item_rect)
            else:
                pygame.draw.rect(screen, BLACK, item_rect)
            
            # Border
            border_color = GREEN if is_hovered else WHITE
            border_width = 1 if is_hovered else 1  # Very thin borders
            pygame.draw.rect(screen, border_color, item_rect, border_width)
            
            # Get difficulty color based on version
            def get_difficulty_color(version_str):
                version_lower = version_str.lower()
                if 'easy' in version_lower or 'beginner' in version_lower:
                    return (100, 200, 255)  # Light blue
                elif 'medium' in version_lower or 'platter' in version_lower:
                    return (150, 220, 150)  # Medium light green
                elif 'normal' in version_lower or 'basic' in version_lower:
                    return (100, 255, 100)  # Green
                elif 'hard' in version_lower or 'advanced' in version_lower:
                    return (255, 200, 100)  # Orange
                elif 'expert' in version_lower or 'insane' in version_lower:
                    return (255, 100, 100)  # Red
                elif 'extra' in version_lower or 'challenge' in version_lower or 'master' in version_lower:
                    return (200, 100, 255)  # Purple
                else:
                    return (200, 200, 200)  # Gray
            
            difficulty_color = get_difficulty_color(version)
            
            # Draw star icon on the left
            star_size = 18
            star_x = item_rect.x + 25  # Further from left edge
            star_y = item_rect.y + item_rect.height // 2
            
            # Draw 5-pointed star
            import math
            star_points = []
            for i in range(10):
                angle = math.pi / 2 + (2 * math.pi * i / 10)  # Start from top
                radius = star_size // 2 if i % 2 == 0 else star_size // 4
                px = star_x + int(radius * math.cos(angle))
                py = star_y - int(radius * math.sin(angle))
                star_points.append((px, py))
            pygame.draw.polygon(screen, difficulty_color, star_points)
            
            # Title on left (after star), centered vertically
            max_title_width = item_rect.width * 0.6  # 60% for title
            title_str = title
            title_surface = font_item_title.render(title_str, True, WHITE)
            
            # Truncate title if too long
            while title_surface.get_width() > max_title_width and len(title_str) > 3:
                title_str = title_str[:-1]
                title_surface = font_item_title.render(title_str + "...", True, WHITE)
            
            if len(title_str) < len(title) and not title_str.endswith("..."):
                title_str += "..."
                title_surface = font_item_title.render(title_str, True, WHITE)
            
            title_y = item_rect.y + (item_rect.height - title_surface.get_height()) // 2
            screen.blit(title_surface, (star_x + star_size + 10, title_y))
            
            # Difficulty on the right, centered vertically
            version_surface = font_item_version.render(version, True, difficulty_color)
            version_x = item_rect.x + item_rect.width - version_surface.get_width() - 10
            version_y = item_rect.y + (item_rect.height - version_surface.get_height()) // 2
            screen.blit(version_surface, (version_x, version_y))
        
        # Draw info panel for hovered item
        if hovered_index is not None and hovered_index < len(level_metadata):
            json_path, title, version, artist, creator, bg_path, note_count, bpm_text, nps_text, length = level_metadata[hovered_index]
            
            # Lazy load background image for info panel
            bg_image = None
            if bg_path:
                if bg_path in image_cache:
                    bg_image = image_cache[bg_path]
                elif os.path.exists(bg_path):
                    try:
                        bg_image = pygame.image.load(bg_path)
                        image_cache[bg_path] = bg_image
                    except:
                        pass
            
            # Info panel background
            info_panel_rect = pygame.Rect(info_panel_x, 120, window_width - info_panel_x - 50, window_height - 200)
            info_bg = pygame.Surface((info_panel_rect.width, info_panel_rect.height))
            info_bg.set_alpha(30)
            info_bg.fill(WHITE)
            screen.blit(info_bg, info_panel_rect)
            pygame.draw.rect(screen, GRAY, info_panel_rect, 2)
            
            # Display level info
            info_y = info_panel_rect.y + 20
            info_x = info_panel_rect.x + 20
            max_text_width = info_panel_rect.width - 40
            
            # Get difficulty color
            def get_difficulty_color(version_str):
                version_lower = version_str.lower()
                if 'easy' in version_lower or 'beginner' in version_lower:
                    return (100, 200, 255)  # Light blue
                elif 'medium' in version_lower or 'platter' in version_lower:
                    return (150, 220, 150)  # Medium light green
                elif 'normal' in version_lower or 'basic' in version_lower:
                    return (100, 255, 100)  # Green
                elif 'hard' in version_lower or 'advanced' in version_lower:
                    return (255, 200, 100)  # Orange
                elif 'expert' in version_lower or 'insane' in version_lower:
                    return (255, 100, 100)  # Red
                elif 'extra' in version_lower or 'challenge' in version_lower or 'master' in version_lower:
                    return (200, 100, 255)  # Purple
                else:
                    return (200, 200, 200)  # Gray
            
            difficulty_color = get_difficulty_color(version)
            
            # Title (with wrapping)
            title_lines = wrap_text(title, font_item_title, max_text_width)
            for line in title_lines:
                title_surface = font_item_title.render(line, True, WHITE)
                screen.blit(title_surface, (info_x, info_y))
                info_y += 40
            info_y += 10
            
            # Version/Difficulty (with wrapping) - use difficulty color
            version_lines = wrap_text(f"Difficulty: {version}", font_item_version, max_text_width)
            for line in version_lines:
                version_surface = font_item_version.render(line, True, difficulty_color)
                screen.blit(version_surface, (info_x, info_y))
                info_y += 28
            info_y += 7
            
            # Artist (with wrapping)
            artist_lines = wrap_text(f"Artist: {artist}", font_item_version, max_text_width)
            for line in artist_lines:
                artist_surface = font_item_version.render(line, True, GRAY)
                screen.blit(artist_surface, (info_x, info_y))
                info_y += 28
            info_y += 7
            
            # Creator (with wrapping)
            if creator and creator != "Unknown":
                creator_lines = wrap_text(f"Charter: {creator}", font_item_version, max_text_width)
                for line in creator_lines:
                    creator_surface = font_item_version.render(line, True, GRAY)
                    screen.blit(creator_surface, (info_x, info_y))
                    info_y += 28
                info_y += 7
            
            # Statistics
            info_y += 10
            if length is not None:
                length_sec = length  # your float seconds
                total_seconds = int(length_sec)          # 125.9 -> 125
                minutes, seconds = divmod(total_seconds, 60)
                stats_title = font_item_version.render(f"Length: {minutes:02d}:{seconds:02d}", True, BLUE)
                screen.blit(stats_title, (info_x + 10, info_y))
                info_y += 30
            
            # Note count
            notes_surface = font_item_version.render(f"Notes: {note_count}", True, BLUE)
            screen.blit(notes_surface, (info_x + 10, info_y))
            info_y += 28
            
            # BPM
            bpm_surface = font_item_version.render(f"BPM: {bpm_text}", True, BLUE)
            screen.blit(bpm_surface, (info_x + 10, info_y))
            info_y += 28
            
            # Notes per second
            nps_surface = font_item_version.render(f"Density: {nps_text} NPS", True, BLUE)
            screen.blit(nps_surface, (info_x + 10, info_y))
            info_y += 35
            
            # Background preview (larger)
            if bg_image:
                try:
                    preview_max_width = info_panel_rect.width - 40
                    preview_max_height = info_panel_rect.height - (info_y - info_panel_rect.y) - 40
                    
                    bg_width, bg_height = bg_image.get_size()
                    scale_x = preview_max_width / bg_width
                    scale_y = preview_max_height / bg_height
                    scale = min(scale_x, scale_y)
                    
                    preview_width = int(bg_width * scale)
                    preview_height = int(bg_height * scale)
                    
                    bg_preview = pygame.transform.scale(bg_image, (preview_width, preview_height))
                    
                    preview_x = info_x + (preview_max_width - preview_width) // 2
                    screen.blit(bg_preview, (preview_x, info_y + 10))
                except:
                    pass
        
        pygame.display.flip()
        clock.tick(60)
    
    return selected_level
