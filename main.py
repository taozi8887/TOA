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

__version__ = "0.3.1"

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
    DARK_BLUE = (50, 100, 200)
    
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
            
            # Draw title (larger, with white color for better visibility on images)
            # Calculate vertical centering for all text elements
            total_text_height = 40  # Title height
            if version:
                total_text_height += 30  # Version height
            if artist and artist != 'Unknown':
                total_text_height += 25
            if creator and creator != 'Unknown':
                total_text_height += 25
            
            # Start y position to center all text
            text_start_y = item_rect.top + (item_rect.height - total_text_height) // 2
            
            text_color = WHITE if bg_image is not None else BLACK
            title_text = font_item_title.render(title, True, text_color)
            title_rect = title_text.get_rect(left=item_rect.left + 30, top=text_start_y)
            screen.blit(title_text, title_rect)
            
            current_y = text_start_y + 40
            
            # Draw version (smaller, below title)
            if version:
                version_text = font_item_version.render(f"[{version}]", True, text_color)
                version_rect = version_text.get_rect(left=item_rect.left + 30, top=current_y)
                screen.blit(version_text, version_rect)
                current_y += 30
            
            # Draw artist and creator (even smaller, below version)
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
        
        # Draw scroll hint
        if total_content_height > available_height:
            visible_start = int(scroll_offset / item_height) + 1
            visible_end = min(len(level_metadata), int((scroll_offset + available_height) / item_height) + 1)
            hint_text = font_hint.render(f"Showing {visible_start}-{visible_end} of {len(level_metadata)} | Scroll or use Arrow Keys", True, GRAY)
            hint_rect = hint_text.get_rect(center=(window_width // 2, window_height - 30))
            screen.blit(hint_text, hint_rect)
        
        # Draw ESC hint
        esc_text = font_hint.render("Press ESC to quit", True, GRAY)
        esc_rect = esc_text.get_rect(center=(window_width // 2, window_height - 60))
        screen.blit(esc_text, esc_rect)
        
        # Fade in from black on first frame (after everything is rendered)
        if first_frame:
            first_frame = False
            # Update display with the fully rendered frame
            pygame.display.flip()
            
            # Now create fade-in effect by drawing black overlay with decreasing alpha
            fade_surface = pygame.Surface((window_width, window_height))
            fade_surface.fill((0, 0, 0))
            fade_start_time = time.time()
            fade_duration = 0.5 if not fade_in_start else 0.7  # Faster on first load, slower when returning
            
            # Save the current fully rendered screen
            saved_screen = screen.copy()
            
            while time.time() - fade_start_time < fade_duration:
                elapsed = time.time() - fade_start_time
                alpha = int(255 * (1 - elapsed / fade_duration))
                
                # Blit the saved fully rendered frame
                screen.blit(saved_screen, (0, 0))
                
                # Apply fade overlay
                fade_surface.set_alpha(alpha)
                screen.blit(fade_surface, (0, 0))
                pygame.display.flip()
                clock.tick(60)
        
        pygame.display.flip()
        clock.tick(60)
    
    if selected_level == "QUIT":
        return None
    
    # Fade out before transitioning
    fade_out(screen, duration=0.5)
    
    return selected_level

def show_autoplay_popup():
    """Show popup window to ask about autoplay"""
    screen = pygame.display.get_surface()
    pygame.display.set_caption(f"TOA v{__version__} - Setup")
    pygame.mouse.set_visible(False)  # Hide mouse cursor
    window_width, window_height = screen.get_size()
    clock = pygame.time.Clock()
    
    font_large = pygame.font.Font(None, 72)
    font_small = pygame.font.Font(None, 48)
    
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    
    # Create a function to draw the autoplay popup content
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
    
    # Fade in from black
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
                    # Go back to level selector
                    result = 'BACK'
                    break
                # Ignore all other keys
        
        if result is not None:
            break
        
        # Draw the content
        draw_autoplay_content(screen)
        pygame.display.flip()
        clock.tick(60)
    
    # Fade out before transitioning to game
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
    # Show level selection popup if no level provided
    if level_json is None:
        level_json = show_level_select_popup(fade_in_start=returning_from_game, preloaded_metadata=preloaded_metadata)
        if level_json is None:
            print("No level selected. Exiting...")
            return
    
    # Infer audio directory from level path if not provided
    if audio_dir is None:
        # Extract beatmap name from level filename
        # e.g., "levels/kemomimi_KEMOMIMI EDM SQUAD.json" -> "kemomimi"
        level_filename = os.path.basename(level_json)
        beatmap_name = level_filename.replace('.json', '').split('_')[0]
        audio_dir = f"beatmaps/{beatmap_name}"
    
    # Show popup to ask about autoplay
    autoplay_enabled = show_autoplay_popup()
    
    # If user pressed ESC on autoplay popup, go back to level selector
    if autoplay_enabled == 'BACK':
        screen = pygame.display.get_surface()
        fade_out(screen, duration=0.7)
        return 'RESTART'
    
    # Reuse existing pygame window
    screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
    pygame.display.set_caption(f"TOA v{__version__}")
    pygame.mouse.set_visible(False)  # Hide mouse cursor
    
    # Focus the window
    pygame.event.pump()

    clock = pygame.time.Clock()
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GREY = (150, 150, 150)
    
    # Start with black screen
    screen.fill(BLACK)
    pygame.display.flip()
    
    # Get screen dimensions
    screen_width, screen_height = screen.get_size()
    center_x, center_y = screen_width // 2, screen_height // 2
    
    # Square size and spacing (reduced for more visibility)
    square_size = 100
    spacing = 105
    border_width = 3
    radius = 10
    
    # ESC key tracking
    esc_press_time = 0
    esc_pressed_once = False
    
    # WASD key tracking
    active_key = None  # Tracks which key is currently pressed: 'w', 'a', 's', 'd', or None
    
    # Mouse click tracking
    last_clicked_button = None  # 'left' or 'right'
    click_time = 0  # Time of last click for visual effect duration
    shake_time = 0  # Time of last hit for screen shake
    shake_intensity = 0  # Current shake intensity
    shake_box = None  # Which box index should shake (0=top, 1=right, 2=bottom, 3=left)
    
    # Rhythm game variables
    game_start_time = time.time()
    current_event_index = 0
    score = 0
    total_hits = 0  # Track successful hits
    total_notes = 0  # Track total notes attempted
    accuracy_window = 0.15  # seconds - time window to hit the target
    
    # Load level from JSON file
    with open(resource_path(level_json), "r") as f:
        level_data = json.load(f)
    
    # Convert JSON level format to tuple format (time, box, color, hitsound_data)
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
    
    # Current target box and color
    target_box = None
    target_color = None
    target_time = None
    target_hitsound = None
    
    # Track active boxes for fading (box_index: (color, flash_start_time, fade_end_time))
    active_boxes = {}
    
    # Track approach indicators - list of (box_index, color, target_time, approach_duration, event_index)
    approach_indicators = []
    
    # Load and scale box image
    box_image = pygame.image.load(resource_path("assets/box.jpg"))
    box_image = pygame.transform.scale(box_image, (square_size, square_size))
    
    # Load and scale colored box overlays
    box_red_image = pygame.image.load(resource_path("assets/boxred.jpg"))
    box_red_image = pygame.transform.scale(box_red_image, (square_size, square_size))
    box_blue_image = pygame.image.load(resource_path("assets/boxblue.jpg"))
    box_blue_image = pygame.transform.scale(box_blue_image, (square_size, square_size))
    
    # Load and scale dot images (reduced size)
    dot_image = pygame.image.load(resource_path("assets/dot.jpg"))
    dot_image = pygame.transform.scale(dot_image, (50, 50))
    dot2_image = pygame.image.load(resource_path("assets/dot2.jpg"))
    dot2_image = pygame.transform.scale(dot2_image, (50, 50))
    
    # Load background music - find first .mp3 file in audio_dir
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
        audio_path = os.path.join(audio_dir, "audio.mp3")  # Fallback
    
    pygame.mixer.music.load(resource_path(audio_path))
    music_start_time = None  # Will be set 3 seconds after game starts
    
    # Load hitsounds (normal, whistle, finish, clap)
    hitsounds = {}
    try:
        # Try to load from beatmap folder first, then default
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = None
            # Try beatmap-specific hitsounds
            for prefix in ['normal', 'soft', 'drum']:
                sound_file = f"{prefix}-hit{sound_name}.wav"
                sound_path = os.path.join(audio_dir, sound_file)
                if os.path.exists(resource_path(sound_path)):
                    sound = pygame.mixer.Sound(resource_path(sound_path))
                    break
            # If not found, use default pygame sound (generate simple beep)
            if sound is None:
                # Create simple beep sounds as fallback
                sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)  # Placeholder
            sound.set_volume(0.6)  # Set volume to 60%
            hitsounds[sound_name] = sound
    except Exception as e:
        print(f"Could not load hitsounds: {e}")
        # Create empty sound objects
        for sound_name in ['normal', 'whistle', 'finish', 'clap']:
            sound = pygame.mixer.Sound(buffer=b'\x00' * 1000)
            sound.set_volume(0.6)  # Set volume to 60%
            hitsounds[sound_name] = sound
    
    # Load beatmap background image if available
    beatmap_bg_image = None
    try:
        # Find first image file in the audio_dir (beatmap folder)
        for file in os.listdir(resource_path(audio_dir)):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                bg_path = os.path.join(audio_dir, file)
                bg_img = pygame.image.load(resource_path(bg_path))
                # Scale to height of 150 while maintaining aspect ratio
                original_width, original_height = bg_img.get_size()
                target_height = 150
                aspect_ratio = original_width / original_height
                target_width = int(target_height * aspect_ratio)
                beatmap_bg_image = pygame.transform.scale(bg_img, (target_width, target_height))
                break
    except Exception as e:
        print(f"Could not load beatmap background: {e}")
        beatmap_bg_image = None
    
    # Create rounded corner version of image
    def create_rounded_image(image, radius):
        """Create an image with rounded corners"""
        size = image.get_size()
        rounded_image = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw the image
        rounded_image.blit(image, (0, 0))
        
        # Create mask for rounded corners
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size[0], size[1]), 0, radius)
        rounded_image.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        
        return rounded_image
    
    box_image_rounded = create_rounded_image(box_image, 8)
    box_red_rounded = create_rounded_image(box_red_image, 8)
    box_blue_rounded = create_rounded_image(box_blue_image, 8)
    
    # Dot animation parameters
    dot_radius = 10

    # How long it takes to move to the next chosen box (seconds)
    move_time = 0

    # Define dot positions (on outside of boxes, 20px from edge towards center)
    def get_dot_positions(cx, cy, size, sp):
        """Dot positions on the INNER sides (toward the middle gap)."""
        inset = 35  # how far from the box edge toward the center (reduced)

        # Box rectangles (same placement logic as your blits)
        top_y    = cy - size - sp
        bottom_y = cy + sp
        left_x   = cx - size - sp
        right_x  = cx + sp

        # Inner edges (facing the center)
        top_inner_edge_y    = top_y + size        # bottom edge of top box
        bottom_inner_edge_y = bottom_y            # top edge of bottom box
        left_inner_edge_x   = left_x + size       # right edge of left box
        right_inner_edge_x  = right_x             # left edge of right box

        return [
            (cx, top_inner_edge_y + inset),       # W: just below top box (toward center)
            (right_inner_edge_x - inset, cy),     # D: just left of right box (toward center)
            (cx, bottom_inner_edge_y - inset),    # S: just above bottom box (toward center)
            (left_inner_edge_x + inset, cy),      # A: just right of left box (toward center)
        ]

    
    def ease_in_out(t):
        """Ease-in-out animation function"""
        return t * t * (3 - 2 * t)

    # --- Dot positioning (4 dots at all positions) ---
    dot_positions = get_dot_positions(center_x, center_y, square_size, spacing)
    # Map keys to indices: 0=top(W), 1=right(D), 2=bottom(S), 3=left(A)
    # ----------------------------------------------------

    # Cache fonts to prevent recreating them every frame (performance)
    font_countdown = pygame.font.Font(None, 120)
    font_judgment = pygame.font.Font(None, 36)
    font_stats = pygame.font.Font(None, 32)
    font_metadata = pygame.font.Font(None, 24)
    font_combo = pygame.font.Font(None, 92)  # Larger font for combo

    # Judgment tracking
    count_300 = 0
    count_100 = 0
    count_50 = 0
    count_miss = 0
    judgment_displays = []  # List of (text, x, y, start_time)
    
    # Combo tracking
    combo = 0
    combo_pop_time = 0  # Time when combo was last increased
    combo_animation_duration = 0.08  # Animation duration in seconds (faster)
    
    # Track events that have already shown visual feedback (shake + text)
    events_with_visual_feedback = set()

    # Pause functionality
    paused = False
    pause_start_time = 0
    total_pause_duration = 0
    paused_elapsed_time = 0  # Frozen elapsed_time when paused

    # Fade-in effect for game start
    fade_in_alpha = 255  # Start fully black
    fade_in_duration = 1.0  # Fade in over 1 second to allow bars to render
    fade_in_delay = 0.3  # Delay before starting fade to let elements render

    running = True
    while running:
        elapsed_time = time.time() - game_start_time - total_pause_duration
        
        # Update fade-in alpha (fade from black to fully visible after delay)
        if elapsed_time < fade_in_delay:
            fade_in_alpha = 255  # Stay fully black during delay
        elif elapsed_time < fade_in_delay + fade_in_duration:
            fade_progress = (elapsed_time - fade_in_delay) / fade_in_duration
            fade_in_alpha = int(255 * (1 - fade_progress))
        else:
            fade_in_alpha = 0
        
        # Use frozen time when paused, current time when not paused
        display_time = paused_elapsed_time if paused else elapsed_time
        
        # Start music 3 seconds after game starts
        if music_start_time is None and elapsed_time >= 3.0 and not paused:
            pygame.mixer.music.play(-1)  # -1 means loop indefinitely
            music_start_time = time.time()

        # Set current target for this frame (do not auto-skip yet so late inputs in this frame still register)
        if current_event_index < len(level):
            target_time, target_box, target_color, target_hitsound = level[current_event_index]
        
        # Show visual feedback (shake + text) when tile hits the box, independent of player input
        if not paused and current_event_index < len(level):
            if elapsed_time >= target_time and current_event_index not in events_with_visual_feedback:
                # Visual feedback for tile hitting box
                import random
                box_centers_display = [
                    (center_x, center_y - square_size // 2 - spacing),
                    (center_x + square_size // 2 + spacing, center_y),
                    (center_x, center_y + square_size // 2 + spacing),
                    (center_x - square_size // 2 - spacing, center_y),
                ]
                jx, jy = box_centers_display[target_box]
                side = random.choice([-1, 1])
                
                # Trigger shake
                shake_time = time.time()
                shake_intensity = 9
                shake_box = target_box
                
                # Play hitsound on miss (tile reached box without being hit)
                hitsounds['normal'].play()
                
                # Mark this event as having shown visual feedback
                events_with_visual_feedback.add(current_event_index)
        
        # Built-in autoplay - directly trigger actions at correct timing (only when not paused)
        if autoplay_enabled and not paused and current_event_index < len(level):
            # Autoplay hits when the time is reached (not before)
            if elapsed_time >= target_time:
                # Set the active key
                active_key = ['w', 'd', 's', 'a'][target_box]
                
                # Calculate judgment
                judgment = 300
                count_300 += 1
                judgment_text = "300"
                combo += 1
                combo_pop_time = time.time()
                combo_pop_time = time.time()
                
                score += judgment
                total_hits += 1
                total_notes += 1
                
                # Add judgment display
                import random
                box_centers_display = [
                    (center_x, center_y - square_size // 2 - spacing),
                    (center_x + square_size // 2 + spacing, center_y),
                    (center_x, center_y + square_size // 2 + spacing),
                    (center_x - square_size // 2 - spacing, center_y),
                ]
                jx, jy = box_centers_display[target_box]
                side = random.choice([-1, 1])
                judgment_displays.append((judgment_text, jx, jy, time.time(), target_box, side))
                
                current_event_index += 1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_time = time.time()
                    if esc_pressed_once and (current_time - esc_press_time) < 2:
                        # Return to level selector
                        pygame.mixer.music.stop()
                        fade_out(screen, duration=0.7)
                        return 'RESTART'
                    else:
                        esc_pressed_once = True
                        esc_press_time = current_time
                
                # Pause toggle with P key
                if event.key == pygame.K_p:
                    paused = not paused
                    if paused:
                        pause_start_time = time.time()
                        paused_elapsed_time = elapsed_time  # Freeze the current time
                        pygame.mixer.music.pause()
                    else:
                        total_pause_duration += time.time() - pause_start_time
                        pygame.mixer.music.unpause()
                
                # Track WASD key presses (only when not paused)
                if not paused:
                    if event.key == pygame.K_w:
                        active_key = 'w'
                    elif event.key == pygame.K_a:
                        active_key = 'a'
                    elif event.key == pygame.K_s or event.key == pygame.K_SPACE:
                        active_key = 's'
                    elif event.key == pygame.K_d:
                        active_key = 'd'
            
            # Removed KEYUP handler - dots persist on last clicked position
            
            if event.type == pygame.MOUSEBUTTONDOWN and not paused:
                # Calculate dynamic accuracy window based on time to next event
                if current_event_index < len(level):
                    next_event_time = level[current_event_index + 1][0] if current_event_index + 1 < len(level) else target_time + 10.0
                    time_to_next = next_event_time - target_time
                    # For long delays (>1s), extend hit window until next event; otherwise use standard window
                    dynamic_accuracy_window = (time_to_next / 2) if time_to_next > 1.0 else accuracy_window
                else:
                    dynamic_accuracy_window = accuracy_window
                
                if event.button == 1:  # Left click
                    # Check if this is the correct action
                    if current_event_index < len(level) and abs(elapsed_time - target_time) < dynamic_accuracy_window:
                        timing_error = abs(elapsed_time - target_time)
                        if active_key == ['w', 'd', 's', 'a'][target_box] and target_color == 'red':
                            # Calculate judgment based on timing
                            if timing_error <= 0.05:  # Perfect hit
                                judgment = 300
                                count_300 += 1
                                judgment_text = "300"
                                combo += 1
                                combo_pop_time = time.time()
                            elif timing_error <= 0.1:  # Good hit
                                judgment = 100
                                count_100 += 1
                                judgment_text = "100"
                                combo += 1
                                combo_pop_time = time.time()
                            elif timing_error <= 0.15:  # OK hit
                                judgment = 50
                                count_50 += 1
                                judgment_text = "50"
                                combo += 1
                                combo_pop_time = time.time()
                            
                            score += judgment
                            total_hits += 1
                            total_notes += 1
                            
                            # Add judgment display at box center
                            import random
                            box_centers_display = [
                                (center_x, center_y - square_size // 2 - spacing),
                                (center_x + square_size // 2 + spacing, center_y),
                                (center_x, center_y + square_size // 2 + spacing),
                                (center_x - square_size // 2 - spacing, center_y),
                            ]
                            jx, jy = box_centers_display[target_box]
                            side = random.choice([-1, 1])
                            judgment_displays.append((judgment_text, jx, jy, time.time(), target_box, side))
                            
                            # Trigger shake on successful hit
                            if current_event_index not in events_with_visual_feedback:
                                shake_time = time.time()
                                shake_intensity = 9
                                shake_box = target_box
                                events_with_visual_feedback.add(current_event_index)
                            
                            # Play hitsounds
                            hitsounds['normal'].play()
                            if target_hitsound.get('whistle'):
                                hitsounds['whistle'].play()
                            if target_hitsound.get('finish'):
                                hitsounds['finish'].play()
                            if target_hitsound.get('clap'):
                                hitsounds['clap'].play()
                            
                            current_event_index += 1
                        else:
                            # Wrong input - display miss and skip this event
                            import random
                            box_centers_display = [
                                (center_x, center_y - square_size // 2 - spacing),
                                (center_x + square_size // 2 + spacing, center_y),
                                (center_x, center_y + square_size // 2 + spacing),
                                (center_x - square_size // 2 - spacing, center_y),
                            ]
                            jx, jy = box_centers_display[target_box]
                            side = random.choice([-1, 1])
                            judgment_displays.append(("miss", jx, jy, time.time(), target_box, side))
                            current_event_index += 1
                            count_miss += 1
                            total_notes += 1
                            combo = 0  # Reset combo on miss
                    elif current_event_index < len(level) and active_key == ['w', 'd', 's', 'a'][target_box] and target_color == 'red':
                        # Correct key/color but too early - show miss
                        import random
                        box_centers_display = [
                            (center_x, center_y - square_size // 2 - spacing),
                            (center_x + square_size // 2 + spacing, center_y),
                            (center_x, center_y + square_size // 2 + spacing),
                            (center_x - square_size // 2 - spacing, center_y),
                        ]
                        jx, jy = box_centers_display[target_box]
                        side = random.choice([-1, 1])
                        judgment_displays.append(("miss", jx, jy, time.time(), target_box, side))
                        count_miss += 1
                        total_notes += 1
                        current_event_index += 1
                        combo = 0  # Reset combo on miss
                    else:
                        # Random click when no event - show on active box
                        if active_key in ['w', 'd', 's', 'a']:
                            active_box_idx = ['w', 'd', 's', 'a'].index(active_key)
                            import random
                            box_centers_display = [
                                (center_x, center_y - square_size // 2 - spacing),
                                (center_x + square_size // 2 + spacing, center_y),
                                (center_x, center_y + square_size // 2 + spacing),
                                (center_x - square_size // 2 - spacing, center_y),
                            ]
                            jx, jy = box_centers_display[active_box_idx]
                            side = random.choice([-1, 1])
                            judgment_displays.append(("miss", jx, jy, time.time(), active_box_idx, side))
                elif event.button == 3:  # Right click
                    # Check if this is the correct action
                    if current_event_index < len(level) and abs(elapsed_time - target_time) < dynamic_accuracy_window:
                        timing_error = abs(elapsed_time - target_time)
                        if active_key == ['w', 'd', 's', 'a'][target_box] and target_color == 'blue':
                            # Calculate judgment based on timing
                            if timing_error <= 0.05:  # Perfect hit
                                judgment = 300
                                count_300 += 1
                                judgment_text = "300"
                                combo += 1
                                combo_pop_time = time.time()
                            elif timing_error <= 0.1:  # Good hit
                                judgment = 100
                                count_100 += 1
                                judgment_text = "100"
                                combo += 1
                                combo_pop_time = time.time()
                            elif timing_error <= 0.15:  # OK hit
                                judgment = 50
                                count_50 += 1
                                judgment_text = "50"
                                combo += 1
                                combo_pop_time = time.time()
                            
                            score += judgment
                            total_hits += 1
                            total_notes += 1
                            
                            # Add judgment display at box center
                            import random
                            box_centers_display = [
                                (center_x, center_y - square_size // 2 - spacing),
                                (center_x + square_size // 2 + spacing, center_y),
                                (center_x, center_y + square_size // 2 + spacing),
                                (center_x - square_size // 2 - spacing, center_y),
                            ]
                            jx, jy = box_centers_display[target_box]
                            side = random.choice([-1, 1])
                            judgment_displays.append((judgment_text, jx, jy, time.time(), target_box, side))
                            
                            # Trigger shake on successful hit
                            if current_event_index not in events_with_visual_feedback:
                                shake_time = time.time()
                                shake_intensity = 9
                                shake_box = target_box
                                events_with_visual_feedback.add(current_event_index)
                            
                            # Play hitsounds
                            hitsounds['normal'].play()
                            if target_hitsound.get('whistle'):
                                hitsounds['whistle'].play()
                            if target_hitsound.get('finish'):
                                hitsounds['finish'].play()
                            if target_hitsound.get('clap'):
                                hitsounds['clap'].play()
                            
                            current_event_index += 1
                        else:
                            # Wrong input - display miss and skip this event
                            import random
                            box_centers_display = [
                                (center_x, center_y - square_size // 2 - spacing),
                                (center_x + square_size // 2 + spacing, center_y),
                                (center_x, center_y + square_size // 2 + spacing),
                                (center_x - square_size // 2 - spacing, center_y),
                            ]
                            jx, jy = box_centers_display[target_box]
                            side = random.choice([-1, 1])
                            judgment_displays.append(("miss", jx, jy, time.time(), target_box, side))
                            current_event_index += 1
                            count_miss += 1
                            total_notes += 1
                            combo = 0  # Reset combo on miss
                    elif current_event_index < len(level) and active_key == ['w', 'd', 's', 'a'][target_box] and target_color == 'blue':
                        # Correct key/color but too early - show miss
                        import random
                        box_centers_display = [
                            (center_x, center_y - square_size // 2 - spacing),
                            (center_x + square_size // 2 + spacing, center_y),
                            (center_x, center_y + square_size // 2 + spacing),
                            (center_x - square_size // 2 - spacing, center_y),
                        ]
                        jx, jy = box_centers_display[target_box]
                        side = random.choice([-1, 1])
                        judgment_displays.append(("miss", jx, jy, time.time(), target_box, side))
                        count_miss += 1
                        total_notes += 1
                        current_event_index += 1
                        combo = 0  # Reset combo on miss
                    else:
                        # Random click when no event - show on active box
                        if active_key in ['w', 'd', 's', 'a']:
                            active_box_idx = ['w', 'd', 's', 'a'].index(active_key)
                            import random
                            box_centers_display = [
                                (center_x, center_y - square_size // 2 - spacing),
                                (center_x + square_size // 2 + spacing, center_y),
                                (center_x, center_y + square_size // 2 + spacing),
                                (center_x - square_size // 2 - spacing, center_y),
                            ]
                            jx, jy = box_centers_display[active_box_idx]
                            side = random.choice([-1, 1])
                            judgment_displays.append(("miss", jx, jy, time.time(), active_box_idx, side))
                            
        # After processing input, skip any events that have fully expired
        if not paused:
            elapsed_time = time.time() - game_start_time - total_pause_duration
            while current_event_index < len(level) and elapsed_time > level[current_event_index][0] + accuracy_window:
                # Get the missed event info (missed because we passed the timing window)
                missed_time, missed_box, missed_color, missed_hitsound = level[current_event_index]
                count_miss += 1
                total_notes += 1
                combo = 0  # Reset combo on miss
                # Display miss judgment
                import random
                box_centers_display = [
                    (center_x, center_y - square_size // 2 - spacing),
                    (center_x + square_size // 2 + spacing, center_y),
                    (center_x, center_y + square_size // 2 + spacing),
                    (center_x - square_size // 2 - spacing, center_y),
                ]
                jx, jy = box_centers_display[missed_box]
                side = random.choice([-1, 1])
                judgment_displays.append(("miss", jx, jy, time.time(), missed_box, side))
                # Add screen shake when indicator reaches box without being hit
                current_event_index += 1

            # Refresh target after any auto-advances
            if current_event_index < len(level):
                target_time, target_box, target_color, target_hitsound = level[current_event_index]
                # Add this box to active boxes if not already there
                if target_box not in active_boxes:
                    flash_lead = 0  # Flash when indicator reaches the box
                    fade_duration = 0.2
                    approach_duration = 0.8  # Time for indicator to travel to box
                    next_time = level[current_event_index + 1][0] if current_event_index + 1 < len(level) else target_time + 1.0
                    flash_start = target_time - flash_lead
                    fade_end = next_time
                    active_boxes[target_box] = (target_color, flash_start, fade_end, fade_duration)
            
            # Add approach indicators for all upcoming events (scan ahead)
            # Remove indicators that have reached their target time (faded out)
            approach_indicators = [(box_idx, color, t_time, duration, evt_idx, side) 
                                for box_idx, color, t_time, duration, evt_idx, side in approach_indicators 
                                if elapsed_time <= t_time]
            
            # Add new indicators for events that don't have one yet
            existing_events = {evt_idx for _, _, _, _, evt_idx, _ in approach_indicators}
            approach_duration = 0.8
            lookahead = 10  # Show up to 10 events ahead
            lookback = 5  # Also check recent past events in case we spam-advanced past them
            start_scan = max(0, current_event_index - lookback)
            for i in range(start_scan, min(current_event_index + lookahead, len(level))):
                if i not in existing_events:
                    evt_time, evt_box, evt_color, evt_hitsound = level[i]
                    # Add indicators for events that haven't reached their target time yet
                    if elapsed_time <= evt_time:
                        # For top box (0), tiles come from left only
                        if evt_box == 0:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'left'))
                        # For bottom box (2), tiles come from right only
                        elif evt_box == 2:
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, 'right'))
                        else:
                            # For left/right boxes, add one indicator from their respective side
                            approach_indicators.append((evt_box, evt_color, evt_time, approach_duration, i, None))

        screen.fill(WHITE)
        
        # Calculate screen shake offset
        shake_x, shake_y = 0, 0
        if shake_time > 0:
            time_since_shake = time.time() - shake_time
            if time_since_shake < 0.15:  # Shake for 150ms
                decay = 1 - (time_since_shake / 0.15)
                import random
                shake_x = random.randint(-int(shake_intensity * decay), int(shake_intensity * decay))
                shake_y = random.randint(-int(shake_intensity * decay), int(shake_intensity * decay))
            else:
                shake_time = 0
                shake_intensity = 0
                shake_box = None

        # Box positions mapping: 0=top, 1=right, 2=bottom, 3=left
        # Draw 4 boxes using image with rounded corners
        # Top square (box 0)
        top_shake_x = shake_x if shake_box == 0 else 0
        top_shake_y = shake_y if shake_box == 0 else 0
        screen.blit(box_image_rounded, (center_x - square_size // 2 + top_shake_x, center_y - square_size - spacing + top_shake_y))
        
        # Right square (box 1)
        right_shake_x = shake_x if shake_box == 1 else 0
        right_shake_y = shake_y if shake_box == 1 else 0
        screen.blit(box_image_rounded, (center_x + spacing + right_shake_x, center_y - square_size // 2 + right_shake_y))
        
        # Bottom square (box 2)
        bottom_shake_x = shake_x if shake_box == 2 else 0
        bottom_shake_y = shake_y if shake_box == 2 else 0
        screen.blit(box_image_rounded, (center_x - square_size // 2 + bottom_shake_x, center_y + spacing + bottom_shake_y))
        
        # Left square (box 3)
        left_shake_x = shake_x if shake_box == 3 else 0
        left_shake_y = shake_y if shake_box == 3 else 0
        screen.blit(box_image_rounded, (center_x - square_size - spacing + left_shake_x, center_y - square_size // 2 + left_shake_y))
        
        # Draw colored overlays on big boxes with fade effect
        # Remove expired boxes from active_boxes (only when not paused)
        if not paused:
            active_boxes = {box_idx: data for box_idx, data in active_boxes.items() if elapsed_time <= data[2]}
        
        # Use display_time for rendering
        render_time = display_time
        
        # Define big box positions for overlay
        big_box_positions = [
            (center_x - square_size // 2, center_y - square_size - spacing),  # Top (box 0)
            (center_x + spacing, center_y - square_size // 2),  # Right (box 1)
            (center_x - square_size // 2, center_y + spacing),  # Bottom (box 2)
            (center_x - square_size - spacing, center_y - square_size // 2),  # Left (box 3)
        ]
        
        for box_idx, (box_x, box_y) in enumerate(big_box_positions):
            # Check if this box is active
            if box_idx in active_boxes:
                color, flash_start, fade_end, fade_duration = active_boxes[box_idx]
                flash_sustain_end = fade_end - fade_duration
                
                # Apply shake to overlay position
                overlay_shake_x = shake_x if shake_box == box_idx else 0
                overlay_shake_y = shake_y if shake_box == box_idx else 0
                
                if flash_start <= render_time <= fade_end:
                    # Calculate alpha for fade
                    alpha = 255
                    if render_time > flash_sustain_end:
                        fade_progress = (render_time - flash_sustain_end) / fade_duration
                        alpha = max(0, int(255 * (1 - fade_progress)))

                    # Select the appropriate colored box image
                    colored_box = box_red_rounded if color == 'red' else box_blue_rounded
                    
                    # Create surface with alpha for fading
                    overlay_surface = colored_box.copy()
                    overlay_surface.set_alpha(alpha)
                    
                    # Draw the colored overlay
                    screen.blit(overlay_surface, (box_x + overlay_shake_x, box_y + overlay_shake_y))
        
        # Draw edge flash indicators for upcoming blocks
        edge_flash_height = square_size // 2 + spacing - 10  # Height decreased by 10px (145px)
        edge_flash_duration = 0.25  # Flash for 250ms before block emerges (decreased)
        edge_offset = 0  # Distance from screen edge (at the edge)
        
        for box_idx, color, target_time, approach_duration, event_idx, side in approach_indicators:
            approach_start_time = target_time - approach_duration
            time_until_start = approach_start_time - render_time
            
            # Only show flash in the last duration before the block starts moving
            if 0 <= time_until_start <= edge_flash_duration:
                flash_progress = 1 - (time_until_start / edge_flash_duration)  # 0 to 1
                
                # Fade in quickly, then fade out
                if flash_progress < 0.3:  # First 30% - fade in
                    alpha = int(255 * (flash_progress / 0.3))
                else:  # Last 70% - fade out
                    alpha = int(255 * (1 - (flash_progress - 0.3) / 0.7))
                
                # Define box center positions to get Y coordinate
                box_centers = [
                    (center_x, center_y - square_size // 2 - spacing),  # Top (box 0)
                    (center_x + square_size // 2 + spacing, center_y),  # Right (box 1)
                    (center_x, center_y + square_size // 2 + spacing),  # Bottom (box 2)
                    (center_x - square_size // 2 - spacing, center_y),  # Left (box 3)
                ]
                
                target_x, target_y = box_centers[box_idx]
                
                # Determine edge position based on box and side (offset from screen edge)
                if box_idx == 0:  # Top - from left or right
                    gradient_x = edge_offset if side == 'left' else screen_width - edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = (side == 'left')
                elif box_idx == 1:  # Right - from right edge
                    gradient_x = screen_width - edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = False
                elif box_idx == 2:  # Bottom - from left or right
                    gradient_x = edge_offset if side == 'left' else screen_width - edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = (side == 'left')
                else:  # Left - from left edge
                    gradient_x = edge_offset
                    edge_y = target_y - edge_flash_height // 2
                    is_left = True
                
                # Draw gradient fade effect extending from edge toward center of screen
                flash_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
                gradient_length = 175  # Width decreased to 175px
                max_gradient_alpha = 85  # Maximum opacity for gradient
                
                # Create gradient surface
                gradient_surface = pygame.Surface((gradient_length, edge_flash_height), pygame.SRCALPHA)
                for i in range(gradient_length):
                    if is_left:
                        # Left edge - opaque at edge (i=0), transparent toward center
                        gradient_alpha = int(max_gradient_alpha * (1 - i / gradient_length) * (alpha / 255))
                    else:
                        # Right edge - transparent at left (i=0), opaque at edge (i=gradient_length)
                        gradient_alpha = int(max_gradient_alpha * (i / gradient_length) * (alpha / 255))
                    
                    gradient_color = (*flash_color, gradient_alpha)
                    pygame.draw.rect(gradient_surface, gradient_color, (i, 0, 1, edge_flash_height))
                
                # Position gradient starting from edge, pointing inward
                if is_left:
                    # Left edge - gradient extends right (toward center)
                    final_gradient_x = gradient_x
                else:
                    # Right edge - gradient extends left (toward center)
                    final_gradient_x = gradient_x - gradient_length
                
                screen.blit(gradient_surface, (int(final_gradient_x), int(edge_y)))
        
        # Draw approach indicators (drawn last to appear above all sprites)
        indicator_size = 95
        
        for box_idx, color, target_time, approach_duration, event_idx, side in approach_indicators:
            approach_start_time = target_time - approach_duration
            # Calculate progress (0 = start, 1 = reached target)
            progress = (render_time - approach_start_time) / approach_duration
            progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
            
            # Define box center positions
            box_centers = [
                (center_x, center_y - square_size // 2 - spacing),  # Top (box 0)
                (center_x + square_size // 2 + spacing, center_y),  # Right (box 1)
                (center_x, center_y + square_size // 2 + spacing),  # Bottom (box 2)
                (center_x - square_size // 2 - spacing, center_y),  # Left (box 3)
            ]
            
            # Fixed travel distance for all indicators
            travel_distance = screen_width // 2  # Half screen width
            
            # Define approach directions with fixed distance
            target_x, target_y = box_centers[box_idx]
            if box_idx == 0:  # Top - use side parameter
                start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                start_y = target_y
            elif box_idx == 1:  # Right
                start_x = target_x + travel_distance
                start_y = target_y
            elif box_idx == 2:  # Bottom - use side parameter
                start_x = target_x - travel_distance if side == 'left' else target_x + travel_distance
                start_y = target_y
            else:  # Left
                start_x = target_x - travel_distance
                start_y = target_y
            
            # Interpolate position
            current_x = start_x + (target_x - start_x) * progress
            current_y = start_y + (target_y - start_y) * progress
            
            # Fade in effect (max 245 opacity, 10 less than before)
            alpha = int(245 * min(1.0, progress))
            
            # Draw indicator with alpha
            indicator_color = (255, 0, 0) if color == 'red' else (0, 0, 255)
            indicator_surface = pygame.Surface((indicator_size, indicator_size), pygame.SRCALPHA)
            pygame.draw.rect(indicator_surface, (*indicator_color, alpha), (0, 0, indicator_size, indicator_size), 0, 8)
            screen.blit(indicator_surface, (int(current_x - indicator_size // 2), int(current_y - indicator_size // 2)))
        
        # Draw judgment displays with fade
        import random
        current_time = time.time()
        active_judgments = []
        for judgment_text, jx, jy, start_time, box_idx, side in judgment_displays:
            time_elapsed = current_time - start_time
            fade_duration = 0.4  # Shorter fade
            if time_elapsed < fade_duration:
                # Fade out
                alpha = int(255 * (1 - time_elapsed / fade_duration))
                # Move up slightly with smaller distance
                offset_move = time_elapsed * 20
                
                # Fixed position based on box: 0=top(above), 1=right(top), 2=bottom(below), 3=left(below)
                if box_idx == 0:  # Top box - show above, no rotation
                    display_x = jx
                    display_y = jy - 80 - offset_move
                    judgment_surface = font_judgment.render(judgment_text, True, BLACK)
                elif box_idx == 1:  # Right box - show on top, no rotation
                    display_x = jx
                    display_y = jy - 80 - offset_move
                    judgment_surface = font_judgment.render(judgment_text, True, BLACK)
                elif box_idx == 2:  # Bottom box - show below, no rotation
                    display_x = jx
                    display_y = jy + 100 - offset_move
                    judgment_surface = font_judgment.render(judgment_text, True, BLACK)
                else:  # Left box (3) - show below, no rotation
                    display_x = jx
                    display_y = jy + 100 - offset_move
                    judgment_surface = font_judgment.render(judgment_text, True, BLACK)
                
                judgment_surface.set_alpha(alpha)
                text_rect = judgment_surface.get_rect(center=(int(display_x), int(display_y)))
                screen.blit(judgment_surface, text_rect)
                active_judgments.append((judgment_text, jx, jy, start_time, box_idx, side))
        judgment_displays = active_judgments
        
        # Draw score, accuracy, and completion (numbers left, labels right)
        # Position setup
        stats_start_y = 20
        right_margin = 20  # Margin from right edge
        
        # Draw combo counter (above score, larger, tilted)
        combo_text_str = f"{combo}x"
        combo_surface = font_combo.render(combo_text_str, True, BLACK)
        
        # Calculate animation (only when combo > 0)
        if combo > 0:
            time_since_pop = time.time() - combo_pop_time
            if time_since_pop < combo_animation_duration:
                # Pop animation progress (0 to 1)
                anim_progress = time_since_pop / combo_animation_duration
                # Ease out - start fast, slow down
                ease = 1 - (1 - anim_progress) ** 2
                
                # Scale effect (1.0 to 1.3 and back to 1.0)
                scale = 1.0 + (0.3 * (1 - abs(anim_progress * 2 - 1)))
                scaled_width = int(combo_surface.get_width() * scale)
                scaled_height = int(combo_surface.get_height() * scale)
                combo_surface = pygame.transform.scale(combo_surface, (scaled_width, scaled_height))
                
                # Shake rotation (-3 to 3 degrees, then settling)
                shake_angle = (1 - ease) * 3 * (1 if combo % 2 == 0 else -1)
                rotation_angle = 0 + shake_angle
            else:
                rotation_angle = 0  # No tilt
        else:
            rotation_angle = 0  # No tilt
        
        # Rotate the surface
        rotated_combo = pygame.transform.rotate(combo_surface, rotation_angle)
        combo_rect = rotated_combo.get_rect(bottomleft=(30, screen_height - 130))
        screen.blit(rotated_combo, combo_rect)
        
        # Draw metadata if available
        if 'meta' in level_data and any(k in level_data['meta'] for k in ['title', 'artist', 'creator', 'version']):
            meta = level_data['meta']
            title = meta.get('title', 'Unknown')
            artist = meta.get('artist', 'Unknown')
            creator = meta.get('creator', 'Unknown')
            version = meta.get('version', 'Unknown')
            
            # Draw metadata lines
            metadata_lines = [
                f"{title} - {artist}",
                f"[{version}] by {creator}"
            ]
            
            for i, line in enumerate(metadata_lines):
                meta_text = font_metadata.render(line, True, BLACK)
                meta_rect = meta_text.get_rect(right=screen_width - right_margin, top=stats_start_y + i * 25)
                screen.blit(meta_text, meta_rect)
            
            stats_start_y += len(metadata_lines) * 25 + 10
        
        # Draw beatmap background image if available
        if beatmap_bg_image:
            img_width = beatmap_bg_image.get_width()
            img_height = beatmap_bg_image.get_height()
            # Right-align the image with margin
            img_x = screen_width - img_width - right_margin
            screen.blit(beatmap_bg_image, (img_x, stats_start_y))
            stats_start_y += img_height + 10  # Move stats down below image with spacing
        
        # Calculate stats
        total_possible = total_notes * 300
        accuracy = (score / total_possible * 100) if total_possible > 0 else 100.0
        completion = (current_event_index / len(level) * 100) if len(level) > 0 else 0
        
        # Display stats at bottom left with labels on left, numbers on right
        stats_data = [
            (f"{score}", "Score"),
            (f"{accuracy:.1f}%", "Accuracy"),
            (f"{completion:.1f}%", "Progress")
        ]
        
        left_margin = 20
        stats_bottom_y = screen_height - 20  # Start from bottom
        
        for i, (number, label) in enumerate(reversed(stats_data)):
            y_pos = stats_bottom_y - (i + 1) * 30
            
            # Draw label (left-aligned)
            label_text = font_stats.render(label, True, BLACK)
            label_rect = label_text.get_rect(left=left_margin, top=y_pos)
            screen.blit(label_text, label_rect)
            
            # Draw number (left-aligned after label with spacing)
            number_text = font_stats.render(number, True, BLACK)
            number_rect = number_text.get_rect(left=left_margin + 120, top=y_pos)
            screen.blit(number_text, number_rect)
        
        # Draw all 4 dots, using dot2.jpg for active dot
        dot_size = 50
        for i, (dot_x, dot_y) in enumerate(dot_positions):
            # Determine if this dot is active
            is_active = False
            if i == 0 and active_key == 'w':  # Top
                is_active = True
            elif i == 1 and active_key == 'd':  # Right
                is_active = True
            elif i == 2 and active_key == 's':  # Bottom
                is_active = True
            elif i == 3 and active_key == 'a':  # Left
                is_active = True
            
            # Draw dot (inactive or active image) - no shake applied
            current_dot = dot2_image if is_active else dot_image
            screen.blit(current_dot, (int(dot_x - dot_size // 2), int(dot_y - dot_size // 2)))
        
        # Draw countdown at the start (3, 2, 1) - drawn last to appear above all sprites
        if display_time < 3.0:
            if display_time < 1.0:
                countdown_text = "3"
            elif display_time < 2.0:
                countdown_text = "2"
            else:
                countdown_text = "1"
            
            # Flash effect - pulse the alpha
            flash_cycle = (display_time % 1.0)  # 0 to 1 within each second
            if flash_cycle < 0.15:  # Quick fade in
                alpha = int(255 * (flash_cycle / 0.15))
            else:  # Slow fade out
                alpha = int(255 * (1 - (flash_cycle - 0.15) / 0.85))
            
            # Render countdown text
            countdown_surface = font_countdown.render(countdown_text, True, BLACK)
            countdown_surface.set_alpha(alpha)
            countdown_rect = countdown_surface.get_rect(center=(center_x, center_y))
            screen.blit(countdown_surface, countdown_rect)
        
        # Draw pause overlay if paused
        if paused:
            # Semi-transparent overlay
            pause_overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            pygame.draw.rect(pause_overlay, (0, 0, 0, 128), (0, 0, screen_width, screen_height))
            screen.blit(pause_overlay, (0, 0))
            
            # Pause text
            pause_text = font_countdown.render("PAUSED", True, WHITE)
            pause_rect = pause_text.get_rect(center=(center_x, center_y))
            screen.blit(pause_text, pause_rect)
            
            # Instructions
            instruction_text = font_stats.render("Press P to resume", True, WHITE)
            instruction_rect = instruction_text.get_rect(center=(center_x, center_y + 80))
            screen.blit(instruction_text, instruction_rect)
        
        # Apply fade-in overlay at the start of the game
        if fade_in_alpha > 0:
            fade_overlay = pygame.Surface((screen_width, screen_height))
            fade_overlay.fill((0, 0, 0))
            fade_overlay.set_alpha(fade_in_alpha)
            screen.blit(fade_overlay, (0, 0))
        
        pygame.display.flip()
        clock.tick(60)

    # Cleanup when user closes window (not returning to level selector)
    pygame.mixer.music.stop()
    return None  # Signal complete exit

if __name__ == "__main__":
    # Prevent multiple instances when frozen with PyInstaller
    import multiprocessing
    multiprocessing.freeze_support()
    
    # Configuration
    REGENERATE_LEVEL = False  # Set to True to regenerate from .osz, False to use existing
    
    if REGENERATE_LEVEL:
        # Run batch processor to generate levels from all .osz files
        from batch_process_osz import process_osz_files
        print("Running batch processor to generate levels from .osz files...")
        process_osz_files()
    else:
        # Show loading screen and preload all assets
        preloaded_metadata = show_loading_screen()
        
        if preloaded_metadata is None:
            print("Failed to load assets. Exiting...")
            sys.exit()
        
        # Loop to allow returning to level selector
        returning = False
        while True:
            result = main(returning_from_game=returning, preloaded_metadata=preloaded_metadata)
            if result != 'RESTART':
                break
            returning = True  # Set flag for subsequent iterations
        
        # Cleanup and exit
        pygame.display.quit()
        pygame.quit()
        sys.exit()
        
        # Or specify a level directly:
        # main(level_json="levels/kemomimi_KEMOMIMI EDM SQUAD.json", audio_dir="beatmaps/kemomimi")









