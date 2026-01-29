import pygame
import pygame.gfxdraw
import sys
import os
import time
import math
import json
import subprocess
import threading
from unzip import read_osz_file
from osu_to_level import create_level_json

__version__ = "0.3.3"

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def process_osz_to_level(osz_path, extract_name, output_json, seed=42):
    """
    Process an .osz file: extract it, find the .osu file, and generate a level JSON.

    Args:
        osz_path: Path to the .osz file
        extract_name: Name for the extraction directory (will be beatmaps/{name})
        output_json: Filename for the output JSON file
        seed: Random seed for level generation

    Returns:
        Path to the generated JSON file
    """
    # Create extraction directory path
    extract_dir = f"beatmaps/{extract_name}"

    # Extract the .osz file
    print(f"\n{'='*60}")
    print(f"Processing: {osz_path}")
    print(f"{'='*60}\n")

    osu_files = read_osz_file(osz_path, extract_dir)

    if not osu_files:
        print("Error: No .osu files found in the archive!")
        return None

    # If multiple .osu files, list them and let user choose
    if len(osu_files) > 1:
        print(f"\nFound {len(osu_files)} difficulties:")
        for i, f in enumerate(osu_files):
            print(f"  [{i+1}] {os.path.basename(f)}")

        while True:
            try:
                choice = input(f"\nChoose difficulty [1-{len(osu_files)}]: ")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(osu_files):
                    osu_file = osu_files[choice_idx]
                    print(f"Selected: {os.path.basename(osu_file)}\n")
                    break
                else:
                    print(f"Please enter a number between 1 and {len(osu_files)}")
            except ValueError:
                print("Please enter a valid number")
    else:
        osu_file = osu_files[0]
        print(f"\nUsing beatmap: {os.path.basename(osu_file)}\n")

    # Generate level JSON
    create_level_json(osu_file, output_json, seed=seed)

    print(f"\n{'='*60}")
    print(f"Successfully created: {output_json}")
    print(f"{'='*60}\n")

    return output_json, extract_dir

def fade_out(screen, duration=0.3):
    """Fade out the current screen to black"""
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

    # Ensure fully black at the end
    fade_surface.set_alpha(255)
    screen.blit(fade_surface, (0, 0))
    pygame.display.flip()

def fade_in(screen, content_func, duration=0.3):
    """Fade in from black to the current screen

    Args:
        screen: pygame display surface
        content_func: Function that draws the content (takes screen as argument)
        duration: Duration of fade in seconds
    """
    clock = pygame.time.Clock()
    fade_surface = pygame.Surface(screen.get_size())
    fade_surface.fill((0, 0, 0))

    start_time = time.time()
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        alpha = int(255 * (1 - elapsed / duration))

        # Draw the content
        content_func(screen)

        # Draw fading black overlay
        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

def show_loading_screen():
    """Show loading screen and preload all assets"""
    pygame.init()
    try:
        pygame.mixer.init(buffer=256)  # Lower buffer for reduced audio latency
    except Exception as e:
        print(f"Warning: Could not set low-latency audio buffer: {e}")
    pygame.mixer.set_num_channels(64)  # Increase channels for rapid hitsounds

    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption(f"TOA v{__version__} - Loading")
    pygame.mouse.set_visible(False)
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()

    font_title = pygame.font.Font(None, 72)
    font_status = pygame.font.Font(None, 36)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    BLUE = (100, 150, 255)

    # Start with black screen
    screen.fill(BLACK)
    pygame.display.flip()

    # Fade in the loading screen
    fade_surface = pygame.Surface((window_width, window_height))
    fade_surface.fill((0, 0, 0))
    for alpha in range(255, 0, -25):
        screen.fill(BLACK)
        title_text = font_title.render("TOA", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        screen.blit(title_text, title_rect)

        status_text = font_status.render("Loading...", True, WHITE)
        status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
        screen.blit(status_text, status_rect)

        fade_surface.set_alpha(alpha)
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    # Get available level files
    levels_dir = "levels"
    level_files = []
    try:
        levels_path = resource_path(levels_dir)
        level_files = [f for f in os.listdir(levels_path) if f.endswith('.json')]
        level_files.sort()
    except Exception as e:
        print(f"Error: Could not read levels directory: {levels_dir}")
        print(f"Full error: {e}")
        return None

    if not level_files:
        print("Error: No level files found!")
        return None

    # Load metadata and background images for each level with progress bar
    level_metadata = []
    total_files = len(level_files)

    for idx, level_file in enumerate(level_files):
        # Update progress
        progress = (idx + 1) / total_files

        # Draw loading screen with progress
        screen.fill(BLACK)

        title_text = font_title.render("TOA", True, WHITE)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        screen.blit(title_text, title_rect)

        status_text = font_status.render(f"Loading levels... {idx + 1}/{total_files}", True, WHITE)
        status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
        screen.blit(status_text, status_rect)

        # Draw progress bar
        bar_width = 400
        bar_height = 20
        bar_x = window_width // 2 - bar_width // 2
        bar_y = window_height // 2 + 100

        # Background bar
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=10)
        # Progress bar
        filled_width = int(bar_width * progress)
        if filled_width > 0:
            pygame.draw.rect(screen, BLUE, (bar_x, bar_y, filled_width, bar_height), border_radius=10)

        pygame.display.flip()
        clock.tick(60)

        # Load level metadata
        try:
            with open(resource_path(os.path.join(levels_dir, level_file)), 'r') as f:
                data = json.load(f)
                title = data.get('meta', {}).get('title', 'Unknown')
                version = data.get('meta', {}).get('version', 'Unknown')
                artist = data.get('meta', {}).get('artist', 'Unknown')
                creator = data.get('meta', {}).get('creator', 'Unknown')

                # Find background image from beatmap directory
                beatmap_name = level_file.replace('.json', '').split('_')[0]
                beatmap_dir = f"beatmaps/{beatmap_name}"
                bg_image = None

                try:
                    # Look for image files in beatmap directory
                    if os.path.exists(resource_path(beatmap_dir)):
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                        for file in os.listdir(resource_path(beatmap_dir)):
                            if any(file.lower().endswith(ext) for ext in image_extensions):
                                bg_path = os.path.join(beatmap_dir, file)
                                bg_image = pygame.image.load(resource_path(bg_path))
                                break
                except:
                    bg_image = None

                level_metadata.append((level_file, title, version, artist, creator, bg_image))
        except:
            # If can't read metadata, use filename
            level_metadata.append((level_file, level_file.replace('.json', ''), '', 'Unknown', 'Unknown', None))

    # Show complete message briefly
    screen.fill(BLACK)
    title_text = font_title.render("TOA", True, WHITE)
    title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
    screen.blit(title_text, title_rect)

    status_text = font_status.render("Ready!", True, WHITE)
    status_rect = status_text.get_rect(center=(window_width // 2, window_height // 2 + 50))
    screen.blit(status_text, status_rect)

    # Draw full progress bar
    bar_width = 400
    bar_height = 20
    bar_x = window_width // 2 - bar_width // 2
    bar_y = window_height // 2 + 100
    pygame.draw.rect(screen, BLUE, (bar_x, bar_y, bar_width, bar_height), border_radius=10)

    pygame.display.flip()
    time.sleep(0.3)  # Brief pause to show completion

    # Fade out loading screen
    fade_out(screen, duration=0.5)

    # Keep screen black for transition to level selector
    screen.fill((0, 0, 0))
    pygame.display.flip()

    return level_metadata

def show_level_select_popup(fade_in_start=False, preloaded_metadata=None):
    """Show popup window to select a level

    Args:
        fade_in_start: If True, fade in from black at the start
        preloaded_metadata: Pre-loaded level metadata from loading screen
    """
    levels_dir = "levels"  # Define this first as it's used later

    # Use preloaded metadata if available, otherwise load now
    if preloaded_metadata is not None:
        level_metadata = preloaded_metadata
    else:
        # Fallback: Load metadata now (shouldn't happen with loading screen)
        pygame.init()
        pygame.mixer.set_num_channels(64)  # Increase channels for rapid hitsounds
        level_files = []
        try:
            levels_path = resource_path(levels_dir)
            level_files = [f for f in os.listdir(levels_path) if f.endswith('.json')]
            level_files.sort()
        except Exception as e:
            print(f"Error: Could not read levels directory: {levels_dir}")
            print(f"Full error: {e}")
            return None

        if not level_files:
            print("Error: No level files found!")
            return None

        level_metadata = []
        for level_file in level_files:
            try:
                with open(resource_path(os.path.join(levels_dir, level_file)), 'r') as f:
                    data = json.load(f)
                    title = data.get('meta', {}).get('title', 'Unknown')
                    version = data.get('meta', {}).get('version', 'Unknown')
                    artist = data.get('meta', {}).get('artist', 'Unknown')
                    creator = data.get('meta', {}).get('creator', 'Unknown')
                    beatmap_name = level_file.replace('.json', '').split('_')[0]
                    beatmap_dir = f"beatmaps/{beatmap_name}"
                    bg_image = None
                    try:
                        if os.path.exists(resource_path(beatmap_dir)):
                            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
                            for file in os.listdir(resource_path(beatmap_dir)):
                                if any(file.lower().endswith(ext) for ext in image_extensions):
                                    bg_path = os.path.join(beatmap_dir, file)
                                    bg_image = pygame.image.load(resource_path(bg_path))
                                    break
                    except:
                        bg_image = None
                    level_metadata.append((level_file, title, version, artist, creator, bg_image))
            except:
                level_metadata.append((level_file, level_file.replace('.json', ''), '', 'Unknown', 'Unknown', None))

    # Window setup - fullscreen borderless
    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption(f"TOA v{__version__} - Select Level")
    pygame.mouse.set_visible(True)  # Show mouse in level selector
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()

    font_title = pygame.font.Font(None, 48)
    font_item_title = pygame.font.Font(None, 32)
    font_item_version = pygame.font.Font(None, 22)
    font_hint = pygame.font.Font(None, 24)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (200, 200, 200)
    BLUE = (100, 150, 255)

    # Scrolling setup - pixel-based smooth scrolling
    scroll_offset = 0.0  # Current scroll position in pixels
    item_height = 250
    list_start_y = 100
    list_end_y = window_height - 100  # Extended down more
    available_height = list_end_y - list_start_y
    total_content_height = len(level_metadata) * item_height
    max_scroll = max(0.0, total_content_height - available_height)
    scroll_speed = 50  # Pixels per scroll tick

    # Scrollbar drag tracking
    scrollbar_dragging = False
    drag_start_y = 0
    drag_start_scroll = 0

    # Hover animation tracking
    hover_animations = {}  # {index: animation_progress (0.0 to 1.0)}
    hover_speed = 0.15  # Animation speed per frame

    selected_level = None
    hovered_index = None

    # We'll render once first, then fade in at the end of the first frame
    first_frame = True

    while selected_level is None:
        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                selected_level = "QUIT"
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    selected_level = "QUIT"
                    break
                elif event.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - scroll_speed)
                elif event.key == pygame.K_DOWN:
                    scroll_offset = min(max_scroll, scroll_offset + scroll_speed)

            if event.type == pygame.MOUSEWHEEL:
                scroll_offset = max(0, min(max_scroll, scroll_offset - event.y * scroll_speed))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if clicked on scrollbar thumb
                if total_content_height > available_height:
                    scrollbar_x = window_width - 35
                    scrollbar_y = list_start_y
                    scrollbar_width = 20
                    scrollbar_track_height = list_end_y - list_start_y
                    thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
                    thumb_y = scrollbar_y + int((scroll_offset / max_scroll) * (scrollbar_track_height - thumb_height)) if max_scroll > 0 else scrollbar_y
                    thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)

                    if thumb_rect.collidepoint(mouse_pos):
                        scrollbar_dragging = True
                        drag_start_y = mouse_y
                        drag_start_scroll = scroll_offset
                        continue

                # Check if clicked on a level item
                for i in range(len(level_metadata)):
                    item_y = list_start_y + (i * item_height) - scroll_offset
                    # Only check items that are visible in the viewport
                    if item_y + item_height < list_start_y or item_y > list_end_y:
                        continue
                    item_rect = pygame.Rect(50, item_y, window_width - 100, item_height - 5)
                    if item_rect.collidepoint(mouse_pos):
                        selected_level = resource_path(os.path.join(levels_dir, level_metadata[i][0]))
                        break

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                scrollbar_dragging = False

        # Handle continuous arrow key scrolling (when held down)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            scroll_offset = max(0, scroll_offset - scroll_speed / 6)  # Slower for held keys
        if keys[pygame.K_DOWN]:
            scroll_offset = min(max_scroll, scroll_offset + scroll_speed / 6)

        # Handle scrollbar dragging
        if scrollbar_dragging and total_content_height > available_height:
            scrollbar_track_height = list_end_y - list_start_y
            thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
            drag_delta_y = mouse_y - drag_start_y
            scroll_delta = (drag_delta_y / (scrollbar_track_height - thumb_height)) * max_scroll if max_scroll > 0 else 0
            scroll_offset = max(0, min(max_scroll, drag_start_scroll + scroll_delta))

        # Rendering
        screen.fill(WHITE)

        # Draw title
        title_text = font_title.render("Select a Level", True, BLACK)
        title_rect = title_text.get_rect(center=(window_width // 2, 55))
        screen.blit(title_text, title_rect)

        # Draw level list
        list_start_y = 100
        hovered_index = None

        # Update hover animations
        for i in range(len(level_metadata)):
            item_y = list_start_y + (i * item_height) - scroll_offset
            # Only check items that are visible in the viewport
            if item_y + item_height < list_start_y or item_y > list_end_y:
                continue
            item_rect = pygame.Rect(50, item_y, window_width - 100, item_height - 5)

            # Check if mouse is hovering
            is_hovered = item_rect.collidepoint(mouse_pos)
            if is_hovered:
                hovered_index = i

            # Update hover animation for this item
            if i not in hover_animations:
                hover_animations[i] = 0.0

            if is_hovered:
                # Ease in - increase animation progress
                hover_animations[i] = min(1.0, hover_animations[i] + hover_speed)
            else:
                # Fade out quickly
                hover_animations[i] = max(0.0, hover_animations[i] - hover_speed * 2)

        # Set cursor based on whether hovering over any item
        if hovered_index is not None:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # Set clipping rect to constrain items to viewport
        viewport_rect = pygame.Rect(0, list_start_y, window_width, list_end_y - list_start_y)
        screen.set_clip(viewport_rect)

        # Draw items
        for i in range(len(level_metadata)):
            item_y = list_start_y + (i * item_height) - scroll_offset

            # Skip items that are not visible in the viewport
            if item_y + item_height < list_start_y or item_y > list_end_y:
                continue

            item_rect = pygame.Rect(50, int(item_y), window_width - 100, item_height - 5)

            # Get hover animation progress with ease-in curve
            hover_progress = hover_animations.get(i, 0.0)
            eased_progress = hover_progress * hover_progress  # Quadratic ease-in

            # Get metadata
            level_file, title, version, artist, creator, bg_image = level_metadata[i]

            # Draw background image if available (cover + center positioning)
            if bg_image is not None:
                # Calculate scaling to cover the rect while maintaining aspect ratio
                bg_width, bg_height = bg_image.get_size()
                rect_width, rect_height = item_rect.width, item_rect.height

                scale_x = rect_width / bg_width
                scale_y = rect_height / bg_height
                scale = max(scale_x, scale_y)  # Cover mode - use larger scale

                new_width = int(bg_width * scale)
                new_height = int(bg_height * scale)

                # Scale the image
                scaled_bg = pygame.transform.scale(bg_image, (new_width, new_height))

                # Center crop
                crop_x = (new_width - rect_width) // 2
                crop_y = (new_height - rect_height) // 2
                cropped_bg = scaled_bg.subsurface(pygame.Rect(crop_x, crop_y, rect_width, rect_height))

                # Create a rounded surface for the background
                bg_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                bg_surface.blit(cropped_bg, (0, 0))

                # Apply rounded corners using a mask
                mask_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                pygame.draw.rect(mask_surface, (255, 255, 255, 255), (0, 0, rect_width, rect_height), border_radius=15)
                bg_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

                screen.blit(bg_surface, item_rect.topleft)

                # Draw black to transparent gradient overlay (left to right)
                gradient_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                for x in range(rect_width):
                    # Gradient from black (left) to transparent (right)
                    alpha = int(200 * (1 - x / rect_width))  # 200 max opacity at left, 0 at right
                    pygame.draw.line(gradient_surface, (0, 0, 0, alpha), (x, 0), (x, rect_height))

                screen.blit(gradient_surface, item_rect.topleft)

                # Draw hover overlay with animation (dark overlay)
                if eased_progress > 0.0:
                    hover_alpha = int(100 * eased_progress)
                    hover_overlay = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)
                    pygame.draw.rect(hover_overlay, (0, 0, 0, hover_alpha), (0, 0, rect_width, rect_height), border_radius=15)
                    screen.blit(hover_overlay, item_rect.topleft)
            else:
                # No background image - draw solid color background with hover animation
                GRAY = (200, 200, 200)
                if eased_progress > 0.0:
                    # Interpolate between GRAY and darker gray based on hover progress
                    darken_amount = int(80 * eased_progress)
                    r = max(0, GRAY[0] - darken_amount)
                    g = max(0, GRAY[1] - darken_amount)
                    b = max(0, GRAY[2] - darken_amount)
                    item_color = (r, g, b)
                else:
                    item_color = GRAY
                pygame.draw.rect(screen, item_color, item_rect, border_radius=15)

            # Draw title (larger)
            total_text_height = 40
            if version:
                total_text_height += 30
            if artist and artist != 'Unknown':
                total_text_height += 25
            if creator and creator != 'Unknown':
                total_text_height += 25

            text_start_y = item_rect.top + (item_rect.height - total_text_height) // 2

            text_color = (255, 255, 255) if bg_image is not None else (0, 0, 0)
            title_text = font_item_title.render(title, True, text_color)
            title_rect = title_text.get_rect(left=item_rect.left + 30, top=text_start_y)
            screen.blit(title_text, title_rect)

            current_y = text_start_y + 40

            if version:
                version_text = font_item_version.render(f"[{version}]", True, text_color)
                version_rect = version_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(version_text, version_rect)
                current_y += 30

            if artist and artist != 'Unknown':
                artist_text = font_hint.render(f"Artist: {artist}", True, text_color)
                artist_rect = artist_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(artist_text, artist_rect)
                current_y += 25

            if creator and creator != 'Unknown':
                creator_text = font_hint.render(f"Mapped by: {creator}", True, text_color)
                creator_rect = creator_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(creator_text, creator_rect)

        # Remove clipping rect after drawing items
        screen.set_clip(None)

        # Draw scrollbar if needed
        if total_content_height > available_height:
            scrollbar_x = window_width - 35
            scrollbar_y = list_start_y
            scrollbar_width = 20
            scrollbar_track_height = list_end_y - list_start_y

            # Draw scrollbar track
            track_rect = pygame.Rect(scrollbar_x, scrollbar_y, scrollbar_width, scrollbar_track_height)
            pygame.draw.rect(screen, WHITE, track_rect, border_radius=5)

            # Calculate scrollbar thumb size and position
            thumb_height = max(30, int((available_height / total_content_height) * scrollbar_track_height))
            thumb_y = scrollbar_y + int((scroll_offset / max_scroll) * (scrollbar_track_height - thumb_height)) if max_scroll > 0 else scrollbar_y

            # Draw scrollbar thumb
            thumb_rect = pygame.Rect(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
            pygame.draw.rect(screen, BLACK, thumb_rect, border_radius=5)

        # Draw hints
        if total_content_height > available_height:
            visible_start = int(scroll_offset / item_height) + 1
            visible_end = min(len(level_metadata), int((scroll_offset + available_height) / item_height) + 1)
            hint_text = font_hint.render(f"Showing {visible_start}-{visible_end} of {len(level_metadata)} | Scroll or use Arrow Keys", True, (200, 200, 200))
            hint_rect = hint_text.get_rect(center=(window_width // 2, window_height - 30))
            screen.blit(hint_text, hint_rect)

        esc_text = font_hint.render("Press ESC to quit", True, (200, 200, 200))
        esc_rect = esc_text.get_rect(center=(window_width // 2, window_height - 60))
        screen.blit(esc_text, esc_rect)

        # Fade in on first frame
        if first_frame:
            first_frame = False
            pygame.display.flip()

            fade_surface = pygame.Surface((window_width, window_height))
            fade_surface.fill((0, 0, 0))
            fade_start_time = time.time()
            fade_duration = 0.5 if not fade_in_start else 0.7

            saved_screen = screen.copy()

            while time.time() - fade_start_time < fade_duration:
                elapsed = time.time() - fade_start_time
                alpha = int(255 * (1 - elapsed / fade_duration))

                screen.blit(saved_screen, (0, 0))
                fade_surface.set_alpha(alpha)
                screen.blit(fade_surface, (0, 0))
                pygame.display.flip()
                clock.tick(60)

        pygame.display.flip()
        clock.tick(60)

    if selected_level == "QUIT":
        return None

    fade_out(screen, duration=0.5)
    return selected_level

def show_autoplay_popup():
    """Show popup window to ask about autoplay"""
    screen = pygame.display.get_surface()
    pygame.display.set_caption(f"TOA v{__version__} - Setup")
    pygame.mouse.set_visible(False)
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()

    font_large = pygame.font.Font(None, 72)
    font_small = pygame.font.Font(None, 48)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    def draw_autoplay_content(surf):
        surf.fill(WHITE)
        title_text = font_large.render("Enable Autoplay?", True, BLACK)
        title_rect = title_text.get_rect(center=(window_width // 2, window_height // 2 - 100))
        surf.blit(title_text, title_rect)

        yes_text = font_small.render("Press Y for Yes", True, BLACK)
        yes_rect = yes_text.get_rect(center=(window_width // 2, window_height // 2 + 20))
        surf.blit(yes_text, yes_rect)

        no_text = font_small.render("Press N for No", True, BLACK)
        no_rect = no_text.get_rect(center=(window_width // 2, window_height // 2 + 80))
        surf.blit(no_text, no_rect)

    fade_in(screen, draw_autoplay_content, duration=0.5)

    result = None
    while result is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    result = True
                    break
                elif event.key == pygame.K_n:
                    result = False
                    break
                elif event.key == pygame.K_ESCAPE:
                    result = 'BACK'
                    break

        if result is not None:
            break

        draw_autoplay_content(screen)
        pygame.display.flip()
        clock.tick(60)

    fade_out(screen, duration=0.3)
    return result

def main(level_json=None, audio_dir=None, returning_from_game=False, preloaded_metadata=None):
    """
    Main game function.

    Args:
        level_json: Path to the level JSON file (if None, will show level selection popup)
        audio_dir: Directory containing audio.mp3 (if None, will infer from level_json path)
        returning_from_game: If True, we're returning from game and should fade in level selector
        preloaded_metadata: Pre-loaded level metadata from loading screen
    """
    if level_json is None:
        level_json = show_level_select_popup(fade_in_start=returning_from_game, preloaded_metadata=preloaded_metadata)
        if level_json is None:
            print("No level selected. Exiting...")
            return

    if audio_dir is None:
        level_filename = os.path.basename(level_json)
        beatmap_name = level_filename.replace('.json', '').split('_')[0]
        audio_dir = f"beatmaps/{beatmap_name}"

    autoplay_enabled = show_autoplay_popup()

    if autoplay_enabled == 'BACK':
        screen = pygame.display.get_surface()
        fade_out(screen, duration=0.7)
        return 'RESTART'

    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption(f"TOA v{__version__}")
    pygame.mouse.set_visible(False)

    pygame.event.pump()

    clock = pygame.time.Clock()
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREY = (150, 150, 150)

    screen.fill(BLACK)
    pygame.display.flip()

    screen_width, screen_height = screen.get_size()
    center_x, center_y = screen_width // 2, screen_height // 2

    square_size = 100
    spacing = 105
    border_width = 3
    radius = 10

    esc_press_time = 0
    esc_pressed_once = False

    active_key = None

    last_clicked_button = None
    click_time = 0
    shake_time = 0
    shake_intensity = 0
    shake_box = None

    game_start_time = time.time()
    current_event_index = 0
    score = 0
    total_hits = 0
    total_notes = 0
    accuracy_window = 0.15

    with open(resource_path(level_json), "r") as f:
        level_data = json.load(f)

    level = []
    for event in level_data["level"]:
        hitsound_data = {
            'whistle': event.get('whistle', False),
            'finish': event.get('finish', False),
            'clap': event.get('clap', False)
        }
        level.append((event["t"], event["box"], event["color"], hitsound_data))

    # Offset all level timings by 3 seconds for music delay
    level = [(t + 3.0, box, color, hs) for t, box, color, hs in level]

    target_box = None
    target_color = None
    target_time = None
    target_hitsound = None

    # Track approach indicators - list of (box_index, color, target_time, approach_duration, event_index, side)
    approach_indicators = []

    # Load and scale box image
    box_image = pygame.image.load(resource_path("assets/box.jpg"))
    box_image = pygame.transform.scale(box_image, (square_size, square_size))

    box_red_image = pygame.image.load(resource_path("assets/boxred.jpg"))
    box_red_image = pygame.transform.scale(box_red_image, (square_size, square_size))
    box_blue_image = pygame.image.load(resource_path("assets/boxblue.jpg"))
    box_blue_image = pygame.transform.scale(box_blue_image, (square_size, square_size))

    dot_image = pygame.image.load(resource_path("assets/dot.jpg"))
    dot_image = pygame.transform.scale(dot_image, (50, 50))
    dot2_image = pygame.image.load(resource_path("assets/dot2.jpg"))
    dot2_image = pygame.transform.scale(dot2_image, (50, 50))

    # Load background music
    audio_path = None
    try:
        for file in os.listdir(resource_path(audio_dir)):
            if file.lower().endswith('.mp3'):
                audio_path = os.path.join(audio_dir, file)
                break
        if audio_path is None:
            raise FileNotFoundError("No .mp3 file found in audio directory")
    except Exception as e:
        print(f"Error finding audio file: {e}")
        audio_path = os.path.join(audio_dir, "audio.mp3")

    pygame.mixer.music.load(resource_path(audio_path))
    music_start_time = None

    # Load hitsounds
    hitsounds = {}
    try:
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = None
            for prefix in ['normal', 'soft', 'drum']:
                sound_file = f"{prefix}-hit{sound_name}.wav"
                sound_path = os.path.join(audio_dir, sound_file)
                if os.path.exists(resource_path(sound_path)):
                    sound = pygame.mixer.Sound(resource_path(sound_path))
                    break
            if sound is None:
                sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            sound.set_volume(0.3)
            hitsounds[sound_name] = sound
    except Exception as e:
        print(f"Could not load hitsounds: {e}")
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            sound.set_volume(0.3)
            hitsounds[sound_name] = sound

    # Load beatmap background image if available
    beatmap_bg_image = None
    try:
        for file in os.listdir(resource_path(audio_dir)):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                bg_path = os.path.join(audio_dir, file)
                bg_img = pygame.image.load(resource_path(bg_path))
                original_width, original_height = bg_img.get_size()
                target_height = 150
                aspect_ratio = original_width / original_height
                target_width = int(target_height * aspect_ratio)
                beatmap_bg_image = pygame.transform.scale(bg_img, (target_width, target_height))
                break
    except Exception as e:
        print(f"Could not load beatmap background: {e}")
        beatmap_bg_image = None

    def create_rounded_image(image, radius):
        """Create an image with rounded corners"""
        size = image.get_size()
        rounded_image = pygame.Surface(size, pygame.SRCALPHA)
        rounded_image.blit(image, (0, 0))
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size[0], size[1]), 0, radius)
        rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return rounded_image

    box_image_rounded = create_rounded_image(box_image, 8)
    box_red_rounded = create_rounded_image(box_red_image, 8)
    box_blue_rounded = create_rounded_image(box_blue_image, 8)

    dot_radius = 10
    move_time = 0

    def get_dot_positions(cx, cy, size, sp):
        """Dot positions on the INNER sides (toward the middle gap)."""
        inset = 35
        top_y    = cy - size - sp
        bottom_y = cy + sp
        left_x   = cx - size - sp
        right_x  = cx + sp

        top_inner_edge_y    = top_y + size
        bottom_inner_edge_y = bottom_y
        left_inner_edge_x   = left_x + size
        right_inner_edge_x  = right_x

        return [
            (cx, top_inner_edge_y + inset),
            (right_inner_edge_x - inset, cy),
            (cx, bottom_inner_edge_y - inset),
            (left_inner_edge_x + inset, cy),
        ]

    dot_positions = get_dot_positions(center_x, center_y, square_size, spacing)

    font_countdown = pygame.font.Font(None, 120)
    font_judgment = pygame.font.Font(None, 36)
    font_stats = pygame.font.Font(None, 32)
    font_metadata = pygame.font.Font(None, 24)
    font_combo = pygame.font.Font(None, 92)

    count_300 = 0
    count_100 = 0
    count_50 = 0
    count_miss = 0
    judgment_displays = []

    combo = 0
    combo_pop_time = 0
    combo_animation_duration = 0.08

    # Track events that have already shown "tile reached box" shake
    reached_shake_events = set()
    resolved_events = set()

    paused = False
    pause_start_time = 0
    total_pause_duration = 0
    paused_elapsed_time = 0

    fade_in_alpha = 255
    fade_in_duration = 1.0
    fade_in_delay = 0.3

    # ===== Arrival flash settings (THIS is the "flash once when tile arrives") =====
    arrival_flash_duration = 0.18   # total flash time
    arrival_flash_sustain = 0.03    # full-bright time at the start
    arrival_flash_index = 0         # moving pointer for efficient scanning
    arrival_shake_index = 0  # NEW: drives arrival shake purely by level timing

    # ======= Hitcheck helpers =======

    def key_for_box(box_idx):
        return ['w', 'd', 's', 'a'][box_idx]

    def button_for_color(color):
        return 'left' if color == 'red' else 'right'

    def compute_dynamic_window(evt_idx, base_window):
        if evt_idx >= len(level):
            return base_window
        t0 = level[evt_idx][0]
        t1 = level[evt_idx + 1][0] if evt_idx + 1 < len(level) else t0 + 10.0
        gap = t1 - t0
        return (gap / 2) if gap > 1.0 else base_window

    def judgment_from_error(timing_error):
        if timing_error <= 0.04:
            return 300, "300"
        if timing_error <= 0.1:
            return 100, "100"
        if timing_error <= 0.15:
            return 50, "50"
        return None, None

    def box_centers_display():
        return [
            (center_x, center_y - square_size // 2 - spacing),
            (center_x + square_size // 2 + spacing, center_y),
            (center_x, center_y + square_size // 2 + spacing),
            (center_x - square_size // 2 - spacing, center_y),
        ]

    def add_judgment_text(text, box_idx):
        import random
        cx, cy = box_centers_display()[box_idx]
        side = random.choice([-1, 1])
        judgment_displays.append((text, cx, cy, time.time(), box_idx, side))

    def trigger_box_shake(box_idx, intensity=9):
        nonlocal shake_time, shake_intensity, shake_box
        shake_time = time.time()
        shake_intensity = intensity
        shake_box = box_idx

    def resolve_miss(evt_idx, miss_box_idx):
        nonlocal count_miss, total_notes, combo, current_event_index
        count_miss += 1
        total_notes += 1
        combo = 0
        add_judgment_text("miss", miss_box_idx)
        resolved_events.add(evt_idx)
        current_event_index += 1

    def resolve_hit(evt_idx, hit_box_idx, timing_error):
        nonlocal score, total_hits, total_notes, combo, combo_pop_time, current_event_index
        nonlocal count_300, count_100, count_50
        judgment, text = judgment_from_error(timing_error)
        if judgment is None:
            resolve_miss(evt_idx, hit_box_idx)
            return

        score += judgment
        total_hits += 1
        total_notes += 1
        combo += 1
        combo_pop_time = time.time()

        if judgment == 300:
            count_300 += 1
        elif judgment == 100:
            count_100 += 1
        else:
            count_50 += 1

        add_judgment_text(text, hit_box_idx)
        trigger_box_shake(hit_box_idx, intensity=9)
        hitsounds['normal'].play()

        resolved_events.add(evt_idx)
        current_event_index += 1

    def handle_click(button_name, elapsed_time_local, evt_idx):
        if evt_idx >= len(level):
            return False

        evt_time, evt_box, evt_color, evt_hitsound = level[evt_idx]

        # NEW: cannot judge this note until 0.5s after it spawns on screen
        spawn_time = evt_time - APPROACH_DURATION
        if elapsed_time_local < spawn_time + JUDGE_DELAY_AFTER_SPAWN:
            return False

        dyn_window = compute_dynamic_window(evt_idx, accuracy_window)
        timing_error = abs(elapsed_time_local - evt_time)

        if timing_error > dyn_window:
            return False

        expected_key = key_for_box(evt_box)
        expected_button = button_for_color(evt_color)

        if button_name != expected_button or active_key != expected_key:
            resolve_miss(evt_idx, evt_box)
            return True

        resolve_hit(evt_idx, evt_box, timing_error)
        return True


    running = True
    while running:
        elapsed_time = time.time() - game_start_time - total_pause_duration

        if elapsed_time < fade_in_delay:
            fade_in_alpha = 255
        elif elapsed_time < fade_in_delay + fade_in_duration:
            fade_progress = (elapsed_time - fade_in_delay) / fade_in_duration
            fade_in_alpha = int(255 * (1 - fade_progress))
        else:
            fade_in_alpha = 0

        display_time = paused_elapsed_time if paused else elapsed_time

        if music_start_time is None and elapsed_time >= 3.0 and not paused:
            pygame.mixer.music.play(-1)
            music_start_time = time.time()

        if current_event_index < len(level):
            target_time, target_box, target_color, target_hitsound = level[current_event_index]
        
        # Autoplay
        if autoplay_enabled and not paused and current_event_index < len(level):
            if elapsed_time >= target_time:
                active_key = key_for_box(target_box)

                score += 300
                total_hits += 1
                total_notes += 1
                combo += 1
                combo_pop_time = time.time()
                count_300 += 1

                add_judgment_text("300", target_box)
                resolved_events.add(current_event_index)
                trigger_box_shake(target_box, intensity=9)

                # Play hitsounds during autoplay
                hitsounds['normal'].play()
                current_event_index += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_time = time.time()
                    if esc_pressed_once and (current_time - esc_press_time) < 2:
                        pygame.mixer.music.stop()
                        fade_out(screen, duration=0.7)
                        return 'RESTART'
                    else:
                        esc_pressed_once = True
                        esc_press_time = current_time

                if event.key == pygame.K_p:
                    paused = not paused
                    if paused:
                        pause_start_time = time.time()
                        paused_elapsed_time = elapsed_time
                        pygame.mixer.music.pause()
                    else:
                        total_pause_duration += time.time() - pause_start_time
                        pygame.mixer.music.unpause()

                if not paused:
                    if event.key == pygame.K_w:
                        active_key = 'w'
                    elif event.key == pygame.K_a:
                        active_key = 'a'
                    elif event.key == pygame.K_s or event.key == pygame.K_SPACE:
                        active_key = 's'
                    elif event.key == pygame.K_d:
                        active_key = 'd'

            if event.type == pygame.MOUSEBUTTONDOWN and not paused:
                if display_time < 3.0:
                    continue
                if current_event_index < len(level):
                    if event.button == 1:
                        handle_click('left', elapsed_time, current_event_index)
                    elif event.button == 3:
                        handle_click('right', elapsed_time, current_event_index)

        # Auto-miss past window
        if not paused:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            while current_event_index < len(level) and elapsed_time > level[current_event_index][0] + accuracy_window:
                missed_time, missed_box, missed_color, missed_hitsound = level[current_event_index]
                if current_event_index not in resolved_events:
                    resolve_miss(current_event_index, missed_box)
                else:
                    current_event_index += 1

            if current_event_index < len(level):
                target_time, target_box, target_color, target_hitsound = level[current_event_index]

            # Maintain approach indicators
            approach_indicators = [
                (box_idx, color, t_time, duration, evt_idx, side)
                for box_idx, color, t_time, duration, evt_idx, side in approach_indicators
                if elapsed_time <= t_time
            ]

            existing_events = {evt_idx for _, _, _, _, evt_idx, _ in approach_indicators}
            APPROACH_DURATION = 0.8
            JUDGE_DELAY_AFTER_SPAWN = 0.1

            approach_duration = APPROACH_DURATION
            lookahead = 10
            lookback = 5
            start_scan = max(0, current_event_index - lookback)
            for i in range(start_scan, min(current_event_index + lookahead, len(level))):
                if i not in existing_events:
                    evt_time, evt_box, evt_color, evt_hitsound = level[i]
                    if elapsed_time <= evt_time:
                        if evt_box == 0:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'left'))
                        elif evt_box == 2:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'right'))
                        else:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, None))

            # One-time shake exactly when tile reaches box (TRULY timing-driven; independent of input)
            while arrival_shake_index < len(level) and elapsed_time >= level[arrival_shake_index][0]:
                t_note, box_idx, color, hs = level[arrival_shake_index]
                if arrival_shake_index not in reached_shake_events:
                    reached_shake_events.add(arrival_shake_index)
                    trigger_box_shake(box_idx, intensity=9)
                arrival_shake_index += 1

        screen.fill(WHITE)

        # Screen shake offset
        shake_x, shake_y = 0, 0
        if shake_time > 0:
            time_since_shake = time.time() - shake_time
            if time_since_shake < 0.15:
                decay = 1 - (time_since_shake / 0.15)
                import random
                shake_x = random.randint(-int(shake_intensity * decay), int(shake_intensity * decay))
                shake_y = random.randint(-int(shake_intensity * decay), int(shake_intensity * decay))
            else:
                shake_time = 0
                shake_intensity = 0
                shake_box = None

        # Draw 4 boxes
        top_shake_x = shake_x if shake_box == 0 else 0
        top_shake_y = shake_y if shake_box == 0 else 0
        screen.blit(box_image_rounded, (center_x - square_size // 2 + top_shake_x, center_y - square_size - spacing + top_shake_y))

        right_shake_x = shake_x if shake_box == 1 else 0
        right_shake_y = shake_y if shake_box == 1 else 0
        screen.blit(box_image_rounded, (center_x + spacing + right_shake_x, center_y - square_size // 2 + right_shake_y))

        bottom_shake_x = shake_x if shake_box == 2 else 0
        bottom_shake_y = shake_y if shake_box == 2 else 0
        screen.blit(box_image_rounded, (center_x - square_size // 2 + bottom_shake_x, center_y + spacing + bottom_shake_y))

        left_shake_x = shake_x if shake_box == 3 else 0
        left_shake_y = shake_y if shake_box == 3 else 0
        screen.blit(box_image_rounded, (center_x - square_size - spacing + left_shake_x, center_y - square_size // 2 + left_shake_y))

        # Use frozen time for rendering when paused
        render_time = display_time

        # Big box positions for overlays (no shake here; shake is already on base image)
        big_box_positions = [
            (center_x - square_size // 2, center_y - square_size - spacing),  # Top
            (center_x + spacing, center_y - square_size // 2),                # Right
            (center_x - square_size // 2, center_y + spacing),                # Bottom
            (center_x - square_size - spacing, center_y - square_size // 2),  # Left
        ]

        # ===== Arrival flash overlay (timing-driven; works even if you miss) =====
        # Move pointer forward past old flashes
        while arrival_flash_index < len(level) and render_time > level[arrival_flash_index][0] + arrival_flash_duration:
            arrival_flash_index += 1

        # For each box, keep the strongest flash currently active
        best_flash_alpha = [0, 0, 0, 0]
        best_flash_color = [None, None, None, None]

        j = arrival_flash_index
        # Scan forward only a small window around "now"
        while j < len(level) and level[j][0] <= render_time + arrival_flash_duration:
            t_note, box_idx, color, hs = level[j]
            dt = render_time - t_note
            if 0 <= dt <= arrival_flash_duration:
                if dt <= arrival_flash_sustain:
                    alpha = 255
                else:
                    # linear fade out after sustain
                    fade_t = (dt - arrival_flash_sustain) / (arrival_flash_duration - arrival_flash_sustain)
                    alpha = max(0, int(255 * (1 - fade_t)))

                if alpha > best_flash_alpha[box_idx]:
                    best_flash_alpha[box_idx] = alpha
                    best_flash_color[box_idx] = color
            j += 1

        # Draw the flashes (move WITH the box shake so it doesn't look like the tile shakes)
        for box_idx in range(4):
            alpha = best_flash_alpha[box_idx]
            color = best_flash_color[box_idx]
            if alpha > 0 and color is not None:
                overlay_img = box_red_rounded if color == 'red' else box_blue_rounded
                overlay_surface = overlay_img.copy()
                overlay_surface.set_alpha(alpha)

                bx, by = big_box_positions[box_idx]

                # If this is the currently-shaken box, apply the same shake offset
                if shake_box == box_idx:
                    bx += shake_x
                    by += shake_y

                screen.blit(overlay_surface, (bx, by))


        # Edge flash indicators
        edge_flash_height = square_size // 2 + spacing - 10
        edge_flash_duration = 0.25
        edge_offset = 0

        for box_idx, color, target_time, approach_duration, event_idx, side in approach_indicators:
            approach_start_time = target_time - approach_duration
            time_until_start = approach_start_time - render_time

            if 0 <= time_until_start <= edge_flash_duration:
                flash_progress = 1 - (time_until_start / edge_flash_duration)

                if flash_progress < 0.3:
                    alpha = int(255 * (flash_progress / 0.3))
                else:
                    alpha = int(255 * (1 - (flash_progress - 0.3) / 0.7))

                box_centers = [
                    (center_x, center_y - square_size // 2 - spacing),
                    (center_x + square_size // 2 + spacing, center_y),
                    (center_x, center_y + square_size // 2 + spacing),
                    (center_x - square_size // 2 - spacing, center_y),
                ]

                target_x, target_y = box_centers[box_idx]

                if box_idx == 0:
                    gradient_x = edge_offset if side == 'left' else screen_width - edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = (side == 'left')
                elif box_idx == 1:
                    gradient_x = screen_width - edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = False
                elif box_idx == 2:
                    gradient_x = edge_offset if side == 'left' else screen_width - edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = (side == 'left')
                else:
                    gradient_x = edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = True

                flash_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
                gradient_length = 175
                max_gradient_alpha = 85

                gradient_surface = pygame.Surface((gradient_length, edge_flash_height), pygame.SRCALPHA)
                for i in range(gradient_length):
                    if is_left:
                        gradient_alpha = int(max_gradient_alpha * (1 - i / gradient_length) * (alpha / 255))
                    else:
                        gradient_alpha = int(max_gradient_alpha * (i / gradient_length) * (alpha / 255))
                    gradient_color = (*flash_color, gradient_alpha)
                    pygame.draw.rect(gradient_surface, gradient_color, (i, 0, 1, edge_flash_height))

                final_gradient_x = gradient_x if is_left else gradient_x - gradient_length
                screen.blit(gradient_surface, (int(final_gradient_x), int(edge_y)))

        # Approach indicators
        indicator_size = 95
        for box_idx, color, target_time, approach_duration, event_idx, side in approach_indicators:
            approach_start_time = target_time - approach_duration
            progress = (render_time - approach_start_time) / approach_duration
            progress = max(0.0, min(1.0, progress))

            box_centers = [
                (center_x, center_y - square_size // 2 - spacing),
                (center_x + square_size // 2 + spacing, center_y),
                (center_x, center_y + square_size // 2 + spacing),
                (center_x - square_size // 2 - spacing, center_y),
            ]

            travel_distance = screen_width // 2
            target_x, target_y = box_centers[box_idx]
            if box_idx == 0:
                start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                start_y = target_y
            elif box_idx == 1:
                start_x = target_x + travel_distance
                start_y = target_y
            elif box_idx == 2:
                start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                start_y = target_y
            else:
                start_x = target_x - travel_distance
                start_y = target_y

            current_x = start_x + (target_x - start_x) * progress
            current_y = start_y + (target_y - start_y) * progress

            alpha = int(245 * min(1.0, progress))
            indicator_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
            indicator_surface = pygame.Surface((indicator_size, indicator_size), pygame.SRCALPHA)
            pygame.draw.rect(indicator_surface, (*indicator_color, alpha), (0, 0, indicator_size, indicator_size), 0, 8)
            screen.blit(indicator_surface, (int(current_x - indicator_size // 2), int(current_y - indicator_size // 2)))

        # Judgments
        current_time = time.time()
        active_judgments = []
        for judgment_text, jx, jy, start_time, box_idx, side in judgment_displays:
            time_elapsed = current_time - start_time
            fade_duration = 0.4
            if time_elapsed < fade_duration:
                alpha = int(255 * (1 - time_elapsed / fade_duration))
                offset_move = time_elapsed * 20

                if box_idx == 0:
                    display_x = jx
                    display_y = jy - 80 - offset_move
                elif box_idx == 1:
                    display_x = jx
                    display_y = jy - 80 - offset_move
                elif box_idx == 2:
                    display_x = jx
                    display_y = jy + 100 - offset_move
                else:
                    display_x = jx
                    display_y = jy + 100 - offset_move

                judgment_surface = font_judgment.render(judgment_text, True, BLACK)
                judgment_surface.set_alpha(alpha)
                text_rect = judgment_surface.get_rect(center=(int(display_x), int(display_y)))
                screen.blit(judgment_surface, text_rect)
                active_judgments.append((judgment_text, jx, jy, start_time, box_idx, side))
        judgment_displays = active_judgments

        # Combo
        combo_text_str = f"{combo}x"
        combo_surface = font_combo.render(combo_text_str, True, BLACK)

        if combo > 0:
            time_since_pop = time.time() - combo_pop_time
            if time_since_pop < combo_animation_duration:
                anim_progress = time_since_pop / combo_animation_duration
                ease = 1 - (1 - anim_progress) ** 2
                scale = 1.0 + (0.3 * (1 - abs(anim_progress * 2 - 1)))
                scaled_width = int(combo_surface.get_width() * scale)
                scaled_height = int(combo_surface.get_height() * scale)
                combo_surface = pygame.transform.scale(combo_surface, (scaled_width, scaled_height))
                shake_angle = (1 - ease) * 3 * (1 if combo % 2 == 0 else -1)
                rotation_angle = 0 + shake_angle
            else:
                rotation_angle = 0
        else:
            rotation_angle = 0

        rotated_combo = pygame.transform.rotate(combo_surface, rotation_angle)
        combo_rect = rotated_combo.get_rect(bottomleft=(30, screen_height - 130))
        screen.blit(rotated_combo, combo_rect)

        # Metadata + image
        stats_start_y = 20
        right_margin = 20

        if 'meta' in level_data and any(k in level_data['meta'] for k in ['title', 'artist', 'creator', 'version']):
            meta = level_data['meta']
            title = meta.get('title', 'Unknown')
            artist = meta.get('artist', 'Unknown')
            creator = meta.get('creator', 'Unknown')
            version = meta.get('version', 'Unknown')

            metadata_lines = [
                f"{title} - {artist}",
                f"[{version}] by {creator}"
            ]

            for i, line in enumerate(metadata_lines):
                meta_text = font_metadata.render(line, True, BLACK)
                meta_rect = meta_text.get_rect(right=screen_width - right_margin, top=stats_start_y + i * 25)
                screen.blit(meta_text, meta_rect)

            stats_start_y += len(metadata_lines) * 25 + 10

        if beatmap_bg_image:
            img_width = beatmap_bg_image.get_width()
            img_height = beatmap_bg_image.get_height()
            img_x = screen_width - img_width - right_margin
            screen.blit(beatmap_bg_image, (img_x, stats_start_y))
            stats_start_y += img_height + 10

        # Stats
        total_possible = total_notes * 300
        accuracy = (score / total_possible * 100) if total_possible > 0 else 100.0
        completion = (current_event_index / len(level) * 100) if len(level) > 0 else 0

        stats_data = [
            (f"{score}", "Score"),
            (f"{accuracy:.1f}%", "Accuracy"),
            (f"{completion:.1f}%", "Progress")
        ]

        left_margin = 20
        stats_bottom_y = screen_height - 20

        for i, (number, label) in enumerate(reversed(stats_data)):
            y_pos = stats_bottom_y - (i + 1) * 30
            label_text = font_stats.render(label, True, BLACK)
            label_rect = label_text.get_rect(left=left_margin, top=y_pos)
            screen.blit(label_text, label_rect)

            number_text = font_stats.render(number, True, BLACK)
            number_rect = number_text.get_rect(left=left_margin + 120, top=y_pos)
            screen.blit(number_text, number_rect)

        # Dots
        dot_size = 50
        for i, (dot_x, dot_y) in enumerate(dot_positions):
            is_active = False
            if i == 0 and active_key == 'w':
                is_active = True
            elif i == 1 and active_key == 'd':
                is_active = True
            elif i == 2 and active_key == 's':
                is_active = True
            elif i == 3 and active_key == 'a':
                is_active = True

            current_dot = dot2_image if is_active else dot_image
            screen.blit(current_dot, (int(dot_x - dot_size // 2), int(dot_y - dot_size // 2)))

        # Countdown
        if display_time < 3.0:
            if display_time < 1.0:
                countdown_text = "3"
            elif display_time < 2.0:
                countdown_text = "2"
            else:
                countdown_text = "1"

            flash_cycle = (display_time % 1.0)
            if flash_cycle < 0.15:
                alpha = int(255 * (flash_cycle / 0.15))
            else:
                alpha = int(255 * (1 - (flash_cycle - 0.15) / 0.85))

            countdown_surface = font_countdown.render(countdown_text, True, BLACK)
            countdown_surface.set_alpha(alpha)
            countdown_rect = countdown_surface.get_rect(center=(center_x, center_y))
            screen.blit(countdown_surface, countdown_rect)

        # Pause overlay
        if paused:
            pause_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            pygame.draw.rect(pause_overlay, (0, 0, 0, 128), (0, 0, screen_width, screen_height))
            screen.blit(pause_overlay, (0, 0))

            pause_text = font_countdown.render("PAUSED", True, WHITE)
            pause_rect = pause_text.get_rect(center=(center_x, center_y))
            screen.blit(pause_text, pause_rect)

            instruction_text = font_stats.render("Press P to resume", True, WHITE)
            instruction_rect = instruction_text.get_rect(center=(center_x, center_y + 80))
            screen.blit(instruction_text, instruction_rect)

        # Fade-in overlay
        if fade_in_alpha > 0:
            fade_overlay = pygame.Surface((screen_width, screen_height))
            fade_overlay.fill((0, 0, 0))
            fade_overlay.set_alpha(fade_in_alpha)
            screen.blit(fade_overlay, (0, 0))

        pygame.display.flip()
        clock.tick(60)

    pygame.mixer.music.stop()
    return None

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    REGENERATE_LEVEL = False

    if REGENERATE_LEVEL:
        from batch_process_osz import process_osz_files
        print("Running batch processor to generate levels from .osz files...")
        process_osz_files()
    else:
        preloaded_metadata = show_loading_screen()

        if preloaded_metadata is None:
            print("Failed to load assets. Exiting...")
            sys.exit()

        returning = False
        while True:
            result = main(returning_from_game=returning, preloaded_metadata=preloaded_metadata)
            if result != 'RESTART':
                break
            returning = True

        pygame.display.quit()
        pygame.quit()
        sys.exit()
