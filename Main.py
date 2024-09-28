import csv
import math
import random
import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Color, Rectangle, Rotate, Translate, PushMatrix, PopMatrix


""" Set the window size to be fixed, and the width 
    and height to be 1000 and 700 respectively. Also, it's 
    impossible to resize the window.

"""
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '700')
# Set the maximum FPS
Config.set('graphics', 'maxfps', '60')
# Write config changes
Config.write()


def collides(rect1, rect2):
    # Extract the top-left corner and dimensions of rectangles using tuple unpacking
    r1x, r1y, r1w, r1h = rect1[0][0], rect1[0][1], rect1[1][0], rect1[1][1]
    r2x, r2y, r2w, r2h = rect2[0][0], rect2[0][1], rect2[1][0], rect2[1][1]

    # Check if the rectangles are overlapping (either to the left/right or above/below)
    if (r1x + r1w <= r2x) or (r2x + r2w <= r1x) or (r1y + r1h <= r2y) or (r2y + r2h <= r1y):
        return False

    else:
        return True


def distance(point1, point2):
    return ((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2) ** 0.5


class DataHandler:
    @staticmethod
    # we use static method because we don't need the class, 
    # but the function is related to the use of the object, 
    # and it is convenient for the function to be in the object's namespace.
    def read_leaderboard():
        leaderboard = []
        try:
            with open('leaderboard.csv', 'r') as file:
                for line in file:
                    try:
                        name, score = line.strip().split(',')
                        leaderboard.append((name, score))
                    except ValueError:
                        # This catches lines that don't correctly split into name and score
                        print(f"Skipping malformed line: {line.strip()}")
        except FileNotFoundError:
            print("leaderboard.csv not found. Please check the file path.")
        return leaderboard

    @staticmethod
    def update_leaderboard(name, score, file_path='leaderboard.csv'):
        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([name, score])


class Bullet(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create a rectangle for the bullet with a specific size and source
        with self.canvas:
            self.ellipse = Rectangle(size=(Window.width/100, Window.width/100), source=("./img/bullet.png"))

    def set_pos(self, x, y):
        # Set the position of the bullet
        self.ellipse.pos = (x, y)


class PowerBar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas:
            # Dimension, position and color of the power bar
            self.powerbar_color = Color(0, 2, 1, 1)
            self.powerbar = Rectangle(size=(100, 15), pos=(Window.width/16, Window.height/1.11))


class Rock(Widget):
    def __init__(self, **kwargs):
        super(Rock, self).__init__(**kwargs)
        self.size = (Window.width / 20, Window.height / 20)  # Example size, adjust as needed
        with self.canvas:
            self.rect = Rectangle(source="./img/block.jpeg", pos=self.pos, size=self.size)
    
    # position update mechanism
    def on_pos(self, *args):
        # if the rectangle exists, update its position
        if hasattr(self, 'rect'):
            self.rect.pos = self.pos


class Mirror(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # initialize the cooldown to False
        self.cooldown = False
        with self.canvas:
            self.mirror = Rectangle(size=(300, 30), pos=(Window.width/2, Window.height/1.2))
            self.mirror_color = Color(0, 0, 0, 1)
    
    # start the cooldown, that is used to avoid multiple collisions
    def start_cooldown(self):
        self.cooldown = True
        threading.Timer(0.5, self.reset_cooldown).start()

    def reset_cooldown(self):
        self.cooldown = False


class VerticalMirror(Widget):
    def __init__(self, pos=None, **kwargs):
        super().__init__(**kwargs)
        # the same is done for the vertical mirror
        self.cooldown = False
        
        if pos is None:
            pos = (Window.width/1.2, Window.height/4)
        
        with self.canvas:
            # notice the size proportions have been inverted wrt the horizontal mirror
            self.verticalmirror = Rectangle(size=(30, 270), pos=pos)
            self.verticalmirror_color = Color(1, 1, 1, 1)
    
    def start_cooldown(self):
        self.cooldown = True
        threading.Timer(0.5, self.reset_cooldown).start()

    def reset_cooldown(self):
        self.cooldown = False


class Laser(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # sets the color of the laser
        self.color_target = [random.random() for _ in range(3)]

        with self.canvas:
            self.laser_color = Color(1, 0, 0, 1)
            PushMatrix() # avoid laser rotation
            self.laser_translation = Translate(0, 0)
            self.laser_rotation = Rotate(angle=0, origin=(0, 0))
            self.laser = Rectangle(size=(100, Window.width/100), pos=(0, 0))
            PopMatrix()

    def set_trans_laser(self, x, y):
        self.laser_translation.x = x
        self.laser_translation.y = y

    def set_pos_laser(self, x, y):
        self.laser.pos = (x, y)

    def set_rotation(self, angle):
        self.laser_rotation.angle = angle
    

    def update_color(self, dt):
        # calculates the difference between target color and current
        color_diff = [self.color_target[i] - self.laser_color.rgba[i] for i in range(3)]

        # if the difference is less than 0.01, change the target color
        if all(abs(diff) < 0.01 for diff in color_diff):
            self.color_target = [random.random() for _ in range(3)]

        # renews current color by getting it closer to the target
        new_color = [self.laser_color.rgba[i] + color_diff[i] * dt * 8 for i in range(3)]
        self.laser_color.rgba = new_color + [1]


class Wormhole(Widget):
    def __init__(self, front_pos, front_size, front_image, rear_pos, rear_size, rear_image, **kwargs):
        super(Wormhole, self).__init__(**kwargs)
        self.front = Image(size=front_size, pos=front_pos, source=front_image)
        self.rear = Image(size=rear_size, pos=rear_pos, source=rear_image)
        self.add_widget(self.front)
        self.add_widget(self.rear)    


class Cupcake(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create a rectangle for the bomb with a fixed size and source
        with self.canvas:
            self.ellipse = Rectangle(size=(Window.width/50, Window.width/50), source=("./img/cupcake.png"))

    def set_pos(self, x, y):
        # Set the position of the bomb
        self.ellipse.pos = (x, y)


class Perpetio(Widget):
    def __init__(self, **kwargs):
        super(Perpetio, self).__init__(**kwargs)
        self.size = (Window.width / 20, Window.height / 20)  # Example size, adjust as needed
        with self.canvas:
            self.rect = Rectangle(source="./img/perpetio.jpg", pos=self.pos, size=self.size)
    
    # position update mechanism
    def on_pos(self, *args):
        # if the rectangle exists, update its position
        if hasattr(self, 'rect'):
            self.rect.pos = self.pos


class OptionsButton(RelativeLayout):
    def __init__(self, **kwargs):
        super(OptionsButton, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (50, 50) 
        self.pos_hint = {'right': 0.975, 'top': 0.98}
        # Options Button
        self.options_btn = ImageButton(source='./img/options.png', size=self.size, pos=self.pos, size_hint=self.size_hint)
        self.options_btn.bind(on_press=self.open_options)
        self.add_widget(self.options_btn)
    
    def update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def open_options(self, instance):
        # Root layout with a colored background
        root_layout = BoxLayout(orientation='vertical')
        with root_layout.canvas.before:
            Color(0.949, 0.718, 0.808)  # Set your desired background color here
            self.rect = Rectangle(size=root_layout.size, pos=root_layout.pos)

        root_layout.bind(pos=self.update_rect, size=self.update_rect)

        # Custom title label
        title_label = Label(text='Options', font_size='20sp', 
                            font_name='./Minecraft.ttf',  # Specify the font path
                            size_hint_y=None, height=50, color=(1, 1, 1, 1))

        # Content layout
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        quit_btn = ImageButton(source='./img/quit.png', on_press=self.quit_game)
        resume_btn = ImageButton(source='./img/resume.png', on_press=self.close_options)
        help_btn = ImageButton(source='./img/tut.png', on_press=self.open_help)

        content.add_widget(quit_btn)
        content.add_widget(resume_btn)
        content.add_widget(help_btn)

        # Add custom title and content to the root layout
        root_layout.add_widget(title_label)
        root_layout.add_widget(content)

        # Create the popup without the default title and with no border
        self.popup = Popup(title='', content=root_layout, size_hint=(None, None), size=(400, 400), 
                           background_color=[0, 0, 0, 0])
        self.popup.open()

    def close_options(self, instance):
        self.popup.dismiss()

    def quit_game(self, instance):
        App.get_running_app().stop()
        

    def open_help(self, instance):
        root_layout = BoxLayout(orientation='vertical')
        with root_layout.canvas.before:
            Color(0.949, 0.718, 0.808)  # Set your desired background color here
            self.rect = Rectangle(size=root_layout.size, pos=root_layout.pos)

        root_layout.bind(pos=self.update_rect, size=self.update_rect)

        # Custom title label
        title_label = Label(text='HELP', font_size='30sp', 
                            font_name='./Minecraft.ttf',  # Specify the font path
                            size_hint_y=None, height=50, color=(1, 1, 1, 1))
        
        help_label = Label(text="          \n    \nThe goal is to hit the enemy in little time and few moves. You start with 10.000 points and can only go down, try not to lose points. Press A and D to move your tank! To move the cannon, you must press W and S. To shoot bullets, lasers and bombshells, you must press SPACE, L and K! To increase the power of the bullet, press P and to decrease it, press O.",
                           font_size='20sp', 
                            font_name='./Minecraft.ttf',  # Specify the font path
                            size_hint= (1, None), height=400, color=(1, 1, 1, 1),
                            halign='center', valign='center', text_size=(400, None))

        root_layout.add_widget(title_label)
        root_layout.add_widget(help_label)
        
        help_popup = Popup(title='', content=root_layout, size_hint=(None, None), size=(500, 400), 
                           background_color=[0, 0, 0, 0])
        help_popup.open()


class Music_button(Button):
    # handles music playback, allows the user to click it and turn music on and off
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.size = (50, 50)
        self.size_hint = (None, None)
        self.pos_hint = {'right': 0.92, 'top': 0.98}

        self.music_state = False
        self.song = SoundLoader.load('./music/sweetbip.mp3')
        with self.canvas:
            self.musicbutton = ImageButton(size=self.size, source="./img/musica_on.png")

        # Bind pos and size to update the Rectangle's position and size
        self.bind(pos=self.update_graphics_pos, size=self.update_graphics_pos)

    def update_graphics_pos(self, *args):
        # Update the Rectangle's position and size to match the button
        self.musicbutton.pos = self.pos
        self.musicbutton.size = self.size
    
    def start_music(self):
        if self.song and not self.music_state:
            self.song.play()
            self.song.loop = True
            self.musicbutton.source = './img/musica_on.png'
            self.music_state = True
    
    def stop_music(self):
        if self.song and self.music_state:
            self.song.stop()
            self.musicbutton.source = './img/musica_off.png'
            self.music_state = False
            self.song.stop()
            self.music_state = False

    def on_press(self):
        if self.music_state:
            self.song.stop()
            # changes icon based on the music state
            self.musicbutton.source = './img/musica_off.png'
        else:
            self.song.play()
            self.musicbutton.source = './img/musica_on.png'
        self.music_state = not self.music_state


class ScoreDisplay(Label):
    def __init__(self, score, **kwargs):
        super(ScoreDisplay, self).__init__(**kwargs)
        self.text = f"Score: {score}"
        self.font_size = '20sp'  # Example font size
        self.font_name = './Minecraft.ttf' 
        self.color = (1, 1, 1, 1)  # Text color
        self.size_hint = (None, None)  # Disable size hint to use absolute positioning
        self.pos_hint = {'right': 0.2, 'top': 0.9999}
        self.bind(size=self.adjust_position)

    def update_score(self, new_score):
        self.text = f"Score: {new_score}"
    
    def adjust_position(self, *args):
        self.pos = (10, Window.height - 30)


class ScoreBanner(Label):
    def __init__(self, score, **kwargs):
        super(ScoreBanner, self).__init__(**kwargs)
        self.text = f"Final Score: {score}"
        self.font_size = '40sp'
        self.font_name = './Minecraft.ttf'
        self.color = (1, 1, 1, 1)
        self.size_hint = (None, None)
        self.pos_hint = {'center_x': 0.494, 'center_y': 0.47}


class Level1GameWidget(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set the initial score to 10000 and create a global variable to store the final score
        global final_score_1
        self.score = 10000
        # After 20 seconds, we call the function to start deducing points
        Clock.schedule_once(self.start_deducing_points, 20)
        # Handle keyboard input
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)
        # Initialize the collision variables as False
        self.is_colliding = False
        self.collision_left = False
        self.collision_right = False
        self.bullet_colliding = False
        self.laser_colliding = False
        self.cupcake_colliding = False

        # Load the sound file for the hit sound
        self.hit_sound = SoundLoader.load('./music/explosion.mp3')
    
        # initialize an empty list to keep track of all different rocks
        self.rocks = []
        # Call the functions to create the horizontal and vertical rock walls
        self.create_horizontal_wall()
        self.create_rock_wall(Window.width * 0.5)
        self.create_rock_wall(Window.width * 0.55)

        # Background image, the one that must come on before all the rest
        with self.canvas.before:
            self.background = Rectangle(source="./img/back_1.jpeg", pos=(0, 0), size=(Window.width, Window.height))

        # Create the enemy
        with self.canvas:
            self.enemy = Rectangle(source="./img/winnie.png", pos=(Window.width/1.5, Window.height/18), size=(100, 200))

        # create a vertical mirror in a specific position of the screen
        self.second_mirror_pos = (Window.width/2.5, Window.height/9.4)
        self.second_vertical_mirror = VerticalMirror(pos=self.second_mirror_pos)
        self.add_widget(self.second_vertical_mirror)

        # Create the vertical mirror
        self.verticalmirror = VerticalMirror()
        self.add_widget(self.verticalmirror)

        # Add the music button
        self.music_button = Music_button()
        self.add_widget(self.music_button)

        with self.canvas:

            # the player rectangle
            sizex = Window.width / 15
            sizey = Window.height/15
            posx = Window.width / 30
            posy = Window.height / 15
            Color(1, 1, 1, 1)

            # creation of the rotating cannon
            PushMatrix()  # avoids player's rotation
            cannon_base_x = posx + sizex / 2
            cannon_base_y = posy + sizey / 2
            self.cannon_size = ((sizex/1.35)/4.5, sizey)
            self.cannon_translation = Translate(cannon_base_x, cannon_base_y)
            self.cannon_rotation = Rotate(origin=(0, self.cannon_size[1] / 4))

            self.cannon = Rectangle(source="./img/cannon_new.png", pos=(-self.cannon_size[0] / 2, self.cannon_size[1] / 4), size=self.cannon_size)
            PopMatrix()

            self.player = Rectangle(source="./img/tank.png", pos=(posx, posy), size=(sizex, sizey))

        # Add widgets for all other game elements
        self.bullet = Bullet()
        self.add_widget(self.bullet)
        
        self.cupcake = Cupcake()
        self.add_widget(self.cupcake)

        self.mirror = Mirror()
        self.add_widget(self.mirror)

        self.score_display = ScoreDisplay(self.score)
        self.add_widget(self.score_display)

        self.powerbar = PowerBar()
        self.add_widget(self.powerbar)

        self.laser = Laser()
        self.add_widget(self.laser)

        self.keyPressed = set()
        Clock.schedule_interval(self.update, 0)
        Clock.schedule_interval(self.laser.update_color, 0)

        # Initialize the variables for the bullet, laser and cupcake
        self.bullet_active = False
        self.laser_active = False
        self.cupcake_active = False

    def start_deducing_points(self, dt):
        # Display warning message
        self.warning_label = Label(text="HURRY UP! From now on, you'll lose 10 points per second.",
                                    font_name = './Minecraft.ttf', font_size='20sp', color = (1, 0, 0, 1),
                                    size_hint=(None, None), size=(400, 100),
                                    pos=(Window.width / 2 - 200, Window.height - 300))
        self.add_widget(self.warning_label)

        # Schedule the removal of the warning message after 4 seconds
        Clock.schedule_once(self.remove_warning_message, 4)
        Clock.schedule_interval(self.deduce_points, 1)

    # define a function to remove the warning message, as the callback function for Clock schedule must
    # accept at least one argument (dt, delta time), so passing the function direcly would execute it
    # immediately
    def remove_warning_message(self, dt):
        self.remove_widget(self.warning_label)

    def deduce_points(self, dt):
        # Deduct 10 points from the score every second
        if self.score > 0:
            self.score -= 10
            self.update_score(self.score)
        else:
            # once we reach <=0 points, we stop deducing
            Clock.unschedule(self.deduce_points)

    def update_score(self, new_score):
        # Update the score and the score display, needs to be called every time the score changes
        self.score = new_score
        self.score_display.update_score(new_score)

    def create_rock_wall(self, x_position):
        num_rocks = 10  # Number of rocks in the wall
        rock_height = Window.height / 20 
        starting_y = (Window.height - num_rocks * rock_height) / 2  # Starting y position of the first rock
        rock_x = x_position

        # Moves the rocks down a little bit, as to align them to the floor's surface
        starting_y -= 3.3 * rock_height

        # Generate positions for all rocks: x is fixed, y is calculated based on the rock height
        rock_positions = [(rock_x, starting_y + i * rock_height) for i in range(num_rocks)]

        # for each position, create a rock and add it to the list of rocks (needed for further management)
        for position in rock_positions:
            rock = Rock(pos=position)
            self.add_widget(rock)
            self.rocks.append(rock)

    def create_horizontal_wall(self):
        num_rocks = 10  # Number of rocks in the wall
        rock_width = Window.width / num_rocks  # Calculate each rock's width based on the screen width
        rock_y = Window.height * 0.5  # Fixed y position for the horizontal wall

        # Generate positions for all rocks in the horizontal wall, and the rest is the same as the vertical wall
        rock_positions = [(i * rock_width, rock_y) for i in range(num_rocks)]

        for position in rock_positions:
            rock = Rock(pos=position)
            self.add_widget(rock)
            self.rocks.append(rock)

    def activate_bullet(self):
        # if the bullet isn't active, we can activate it
        if not self.bullet_active:
            self.bullet_active = True
            # each time the bullet is active, we deduct 100 points and update the score
            self.score -= 100
            self.update_score(self.score)
            # define mass, velocity
            self.bullet_mass = 1.5
            self.bullet_velocity = math.sqrt(400*2*self.powerbar.powerbar.size[0]/self.bullet_mass)
            # the starting time will be needed later to calculate the bullet's trajectory
            self.bullet_start_time = Clock.get_boottime()
            # calculate the cannon tip position
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            # establishing bullet starting position, based on the cannon tip position, rotation angle and size
            self.bullet.set_pos(-self.cannon.size[0]/2 + cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), 
                                cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))

            # calculate velocity components based on bullet velocity and cannon angle
            self.bullet_velocity_x = self.bullet_velocity * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.bullet_velocity_y = self.bullet_velocity * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def activate_laser(self):
        # if the laser isn't already active, we activate it
        if not self.laser_active:
            self.laser_active = True
            # score deducted and updated
            self.score -= 100
            self.update_score(self.score)
            # start time for the laser, needed for trajectory calculation
            self.laser_start_time = Clock.get_boottime()
            # define cannon tip position
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            # set laser position based on cannon tip position, size and rotation angle
            self.laser.set_pos_laser(0,0)
            self.laser.set_trans_laser(cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), 
                                       cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))
            self.laser.set_rotation(self.cannon_rotation.angle + 90)
            self.laser_velocity_x = 1500 * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.laser_velocity_y = 1500 * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def activate_cupcake(self):
        # very similar, if not pretty much the same as the bullet activation
        if not self.cupcake_active:
            self.score -= 200
            self.update_score(self.score)
            self.cupcake_active = True
            self.cupcake_mass = 3
            self.cupcake_velocity = math.sqrt(400*2*self.powerbar.powerbar.size[0]/self.cupcake_mass)
            self.cupcake_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.cupcake.set_pos(-self.cannon.size[0]/2 + cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), 
                              cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))
            self.cupcake_velocity_x  = self.cupcake_velocity * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.cupcake_velocity_y = self.cupcake_velocity * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def _on_keyboard_closed(self):
        # Unbind keyboard events when the keyboard is closed
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard.unbind(on_key_up=self._on_key_up)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        # handle key press events
        self.keyPressed.add(text)
        # pressing space will result in bullet activation
        if keycode[1] == 'spacebar' and not self.bullet_active:
            self.activate_bullet()
        # l laser activation
        if keycode[1] == "l" and not self.laser_active:
            self.activate_laser()
        # k cupcake activation
        if keycode[1] == "k" and not self.cupcake_active:
            self.activate_cupcake()

    def _on_key_up(self, keyboard, keycode):
        # handle key release events, by removing released key from the set
        text = keycode[1]
        if text in self.keyPressed:
            self.keyPressed.remove(text)

    def hide_enemy(self):
        # used when the enemy is hit by a bullet, laser or cupcake
        self.music_button.stop_music() # Stop the music
        self.enemy.pos = (-1000, -1000)  # Move the enemy off-screen
        Clock.schedule_once(self.transition_to_intermediate, 1)
        global final_score_1 # Set the final score to the current score
        final_score_1 = self.score 

    def transition_to_intermediate(self, dt):
        # Transition to the intermediate screen, this function is needed because 
        # we can't change screens directly 
        screen_manager = self.parent.manager
        screen_manager.current = 'intermediate' 

    def reflect_laser(self, vertical):
        # Calculate reflection based on the mirror's orientation
        if vertical:
            # Reflect the laser's x velocity
            self.laser_velocity_x *= -1
        else:
            # Reflect the laser's y velocity
            self.laser_velocity_y *= -1

        # Adjust laser rotation based on new velocity vector
        new_angle = math.atan2(self.laser_velocity_y, self.laser_velocity_x)
        self.laser.set_rotation(math.degrees(new_angle))

        # Optionally, move the laser slightly off the mirror to prevent immediate recollision
        offset_distance = 5
        self.laser.laser_translation.x += offset_distance if vertical else 0
        self.laser.laser_translation.y += offset_distance if not vertical else 0

    # Update function to handle game logic
    def update(self, dt):

        # Check for collision with rocks
        for rock in self.rocks:
            if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (rock.rect.pos, rock.rect.size)):
                self.bullet_colliding = True
                self.rocks.remove(rock)
                self.remove_widget(rock)
                if self.hit_sound:
                    # make sure that the previous sound has stopped before playing a new one
                    self.hit_sound.stop()
                    self.hit_sound.play()
                break 
            
        for rock in self.rocks:  # Iterate over a copy of the rocks list
            if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (rock.rect.pos, rock.rect.size)):
                self.cupcake_colliding = True
                affected_rocks = [rock]  # Start with the initially collided rock

                # Find other rocks within the specified radius
                for other_rock in self.rocks:
                    # i had to use a higher radius for the cupcake to work properly, using 1000/50 didn't affect any other rocks 
                    # so it became pretty much useless
                    if other_rock is not rock and distance(rock.rect.pos, other_rock.rect.pos) <= 1000 / 25:
                        affected_rocks.append(other_rock)

                # Apply effects to all affected rocks
                for affected_rock in affected_rocks:
                    if affected_rock in self.rocks:  # Double-check to avoid errors
                        self.rocks.remove(affected_rock)
                        self.remove_widget(affected_rock)

                if self.hit_sound:
                    self.hit_sound.stop()
                    self.hit_sound.play()
                break  # Break after handling the cupcake collision

        # Check for collision with the mirror
        if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.enemy.pos, self.enemy.size)):
            self.laser_colliding = True
            self.hide_enemy()  # Hides the enemy

        # Check for bullet collision with the enemy
        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (self.enemy.pos, self.enemy.size)):
            self.bullet_colliding = True
            self.hide_enemy()  # Hides remove the enemy

        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (self.enemy.pos, self.enemy.size)):
            self.cupcake_colliding = True
            self.hide_enemy()  # Hides remove the enemy
        
        # Check for collision with vertical mirror
        if not self.verticalmirror.cooldown and collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.verticalmirror.verticalmirror.pos, self.verticalmirror.verticalmirror.size)):
            # if the mirror isn't on cooldown, we reflect the laser and start the cooldown
            self.reflect_laser(vertical=True)
            self.verticalmirror.start_cooldown()  # Start cooldown for vertical mirror
        
        if not self.second_vertical_mirror.cooldown and collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.second_vertical_mirror.verticalmirror.pos, self.second_vertical_mirror.verticalmirror.size)):
            self.reflect_laser(vertical=True)
            self.second_vertical_mirror.start_cooldown()  # Start cooldown for vertical mirror

        # Check for collision with horizontal mirror
        if not self.mirror.cooldown and collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.mirror.mirror.pos, self.mirror.mirror.size)):
            self.reflect_laser(vertical=False)
            self.mirror.start_cooldown()  # Start cooldown for horizontal mirror

        # Check for collision with the player, and set the collision variables accordingly
        if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y) ,self.laser.laser.size),(self.enemy.pos,self.enemy.size)):
            self.laser_colliding = True 

        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size),(self.enemy.pos, self.enemy.size)):
            self.bullet_colliding = True
        
        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size),(self.enemy.pos, self.enemy.size)):
            self.bomb_colliding = True

        if collides((self.player.pos, self.player.size), (self.enemy.pos, self.enemy.size)):
            self.is_colliding = True
        else:
            self.is_colliding = False         
        
        # Check for collision with the walls
        if not self.is_colliding:
            self.collision_left = False
            self.collision_right = False

        if self.is_colliding and (self.player.pos[0]<self.enemy.pos[0]):
            self.collision_right = True

        if self.is_colliding and (self.player.pos[0]>self.enemy.pos[0]):
            self.collision_left = True

        step_size = Window.width/8 * dt  # Movement speed
        rotation_speed = 45 * dt  # Rotation speed

        # Player movement and updating of cannon rotation
        if "a" in self.keyPressed and not self.collision_left:
            # Not allowed to go off-screen (on the left)
            new_x = max(self.player.pos[0] - step_size, 0)
            self.player.pos = (new_x, self.player.pos[1])

        if "d" in self.keyPressed and not self.collision_right:
            max_x = (Window.width/3) - self.player.size[0]
            # Not allowed to go off-screen (on the right)
            new_x = min(self.player.pos[0] + step_size, max_x)
            self.player.pos = (new_x, self.player.pos[1])

        # Updating cannon's position
        self.cannon_translation.x = self.player.pos[0] + self.player.size[0] / 2 
        self.cannon_translation.y = self.player.pos[1] + self.player.size[1] / 2

        # Cannon rotation
        if "w" in self.keyPressed:
            if self.cannon_rotation.angle + rotation_speed <= 90:  # Limit to more than +90 degrees
                self.cannon_rotation.angle += rotation_speed
        if "s" in self.keyPressed:
            if self.cannon_rotation.angle - rotation_speed >= -90:  # Limit to less than 90 degrees
                self.cannon_rotation.angle -= rotation_speed

        # Powerbar logic
        if "p" in self.keyPressed and not self.bullet_active:
            if self.powerbar.powerbar.size[0] <= 600:
                self.powerbar.powerbar.size = (self.powerbar.powerbar.size[0] + 5, self.powerbar.powerbar.size[1])
        
        if "o" in self.keyPressed and not self.bullet_active:
            if self.powerbar.powerbar.size[0] >= 100:
                self.powerbar.powerbar.size = (self.powerbar.powerbar.size[0] - 5, self.powerbar.powerbar.size[1])

        if self.bullet_active:
            # Calculate the bullet's trajectory based on the time since it has been activated
            time_elapsed = Clock.get_boottime() - self.bullet_start_time
            x = self.bullet.ellipse.pos[0] + self.bullet_velocity_x * dt
            # y = x0 + v0y * t - 0.5 * g * t^2
            y = self.bullet.ellipse.pos[1] + self.bullet_velocity_y * dt - (0.5 * 9.8 * time_elapsed ** 2)
            self.bullet.set_pos(x, y)

            # Deactivate the bullet if it goes out of the window
            if x > Window.width or y < Window.height/15 or x < 0 or self.bullet_colliding:
                self.bullet_active = False
                self.bullet.set_pos(x, 3000)
                self.bullet_colliding = False

        if self.laser_active:
            # Calculate the laser's trajectory
            x = self.laser.laser_translation.x + self.laser_velocity_x * dt
            y = self.laser.laser_translation.y + self.laser_velocity_y * dt
            # Update the laser's position and rotation
            self.laser.set_trans_laser(x, y)
            self.laser.laser_rotation = self.laser.laser_rotation

            # Deactivate the laser if it goes out of the window
            if x > Window.width or y < Window.height/15 or y> Window.height or x < 0 or self.laser_colliding:
                self.laser_active = False
                self.laser.set_trans_laser(0, 3000)
                self.laser_colliding = False

        if self.cupcake_active:
            # Calculate the cupcake's trajectory (very similar to the bullet)
            time_elapsed = Clock.get_boottime() - self.cupcake_start_time
            x = self.cupcake.ellipse.pos[0] + self.cupcake_velocity_x * dt
            y = self.cupcake.ellipse.pos[1] + self.cupcake_velocity_y * dt - (0.5 * 9.8 * time_elapsed ** 2)
            self.cupcake.set_pos(x, y)

            # DEACTIVATE BOMB if it goes out of the window
            if x > Window.width or y < Window.height/15 or x < 0 or self.cupcake_colliding:
                self.cupcake_active = False
                self.cupcake.set_pos(x, 3000)
                self.cupcake_colliding = False


class Level2GameWidget(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global final_score_1
        self.score = final_score_1
        # define a second global variable to store the final score of this level
        global final_score_2
        # same premises as level 1
        Clock.schedule_once(self.start_deducing_points, 20)
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)
        self.is_colliding = False
        self.collision_left = False
        self.collision_right = False
        self.bullet_colliding = False
        self.laser_colliding = False
        self.cupcake_colliding = False
        
        # Load the sound file for the hit sound
        self.hit_sound = SoundLoader.load('./music/explosion.mp3')
    
        # initialize an empty list to keep track of all different rocks
        self.rocks = []
        self.create_rock_wall()
        self.create_second_rock_wall()
        self.create_horizontal_wall(Window.height * 0.5, Window.width * 0.6, Window.width * 0.8)
        
        self.music_button = Music_button()
        self.add_widget(self.music_button)

        # Background image, the one that must come on before all the rest
        with self.canvas.before:
            self.background = Rectangle(source="./img/back_2.jpeg", pos=(0, 0), size=(Window.width, Window.height))

        with self.canvas:
            # define the enemy
            self.enemy = Rectangle(source="./img/ihoh.png", pos=(Window.width/1.5, Window.height/18), size=(120, 200))

        with self.canvas:
            sizex = Window.width / 15
            sizey = Window.height/15
            posx = Window.width / 30
            posy = Window.height / 15
            Color(1, 1, 1, 1)

            PushMatrix() 
            cannon_base_x = posx + sizex / 2
            cannon_base_y = posy + sizey / 2
            self.cannon_size = ((sizex/1.35)/4.5, sizey)
            self.cannon_translation = Translate(cannon_base_x, cannon_base_y)
            self.cannon_rotation = Rotate(origin=(0, self.cannon_size[1] / 4))

            self.cannon = Rectangle(source="./img/cannon_new.png", pos=(-self.cannon_size[0] / 2, self.cannon_size[1] / 4), size=self.cannon_size)
            PopMatrix()

            self.player = Rectangle(source="./img/tank.png", pos=(posx, posy), size=(sizex, sizey))

        self.bullet = Bullet()
        self.add_widget(self.bullet)

        self.second_mirror_pos = (Window.width/2.3, Window.height/9.4)
        self.second_vertical_mirror = VerticalMirror(pos=self.second_mirror_pos)
        self.add_widget(self.second_vertical_mirror)

        self.cupcake = Cupcake()
        self.add_widget(self.cupcake)

        self.powerbar = PowerBar()
        self.add_widget(self.powerbar)   # spostare sopra per carro rgb

        self.laser = Laser()
        self.add_widget(self.laser)

        self.score_display = ScoreDisplay(self.score)
        self.add_widget(self.score_display)

        # The wormhole is created here, with the front and rear parts being defined directly
        self.wormhole = Wormhole(front_pos=(Window.width/2, Window.height/2), front_size=(100, 200), front_image='./img/rear.png',
                    rear_pos=(Window.width/3, Window.height/4), rear_size=(100, 200), rear_image='./img/front.png')
        self.add_widget(self.wormhole)

        self.keyPressed = set()
        Clock.schedule_interval(self.update, 0)
        Clock.schedule_interval(self.laser.update_color, 0)

        self.bullet_active = False
        self.laser_active = False
        self.cupcake_active = False

    def create_rock_wall(self):
        num_rocks = 10  # Number of rocks in the wall
        rock_height = Window.height / 20 
        starting_y = (Window.height - num_rocks * rock_height) / 2  # Starting y position of the first rock
        rock_x = Window.width * 0.5

        # Moves the rocks down a little bit, as to align them to the floor's surface
        starting_y -= 3.3 * rock_height

        # Generate positions for all rocks: x is fixed, y is calculated based on the rock height
        rock_positions = [(rock_x, starting_y + i * rock_height) for i in range(num_rocks)]

        # for each position, create a rock and add it to the list of rocks (needed for further management)
        for position in rock_positions:
            rock = Rock(pos=position)
            self.add_widget(rock)
            self.rocks.append(rock)
    
    def create_horizontal_wall(self, y_position, x_start, x_end):
        rock_width = Window.width / 20  # Calculate each rock's width based on the screen width
        rock_y = y_position  # Use the passed y_position for the wall's vertical position

        # Calculate the number of rocks based on the specified start and end points
        num_rocks = int((x_end - x_start) / rock_width)

        # Generate positions for all rocks in the horizontal wall, starting from x_start
        rock_positions = [(x_start + i * rock_width, rock_y) for i in range(num_rocks)]

        # Use map to apply add_rock to each position
        for position in rock_positions:
            rock = Rock(pos=position, size=(rock_width, rock_width))  # Assuming square rocks for simplicity
            self.add_widget(rock)
            self.rocks.append(rock)

    def create_second_rock_wall(self):
        num_rocks = 13  # Number of rocks in the wall
        rock_height = Window.height / 20 
        starting_y = (Window.height - num_rocks * rock_height) / 2  # Starting y position of the first rock
        rock_x = Window.width * 0.3
        starting_y -= 1.8 * rock_height

        # Generate positions for all rocks
        rock_positions = [(rock_x, starting_y + i * rock_height) for i in range(num_rocks)]

        for position in rock_positions:
            rock = Rock(pos=position)
            self.add_widget(rock)
            self.rocks.append(rock)

    def teleport_bullet(self, bullet, wormhole_part, wormhole):
        # Calculate the difference between the bullet and the wormhole part
        diff_x = bullet.ellipse.pos[0] - wormhole_part.pos[0]
        diff_y = bullet.ellipse.pos[1] - wormhole_part.pos[1]

        # Determine the exit part of the wormhole
        exit_part = wormhole.front if wormhole_part == wormhole.rear else wormhole.rear

        # Teleport the bullet to the other wormhole part
        bullet.ellipse.pos = (exit_part.pos[0] + diff_x, exit_part.pos[1] + diff_y)     

    def start_deducing_points(self, dt):
        # Display warning message
        self.warning_label = Label(text="HURRY UP! From now on, you'll lose 10 points per second.",
                                    font_name = './Minecraft.ttf', font_size='20sp', color = (1, 0, 0, 1),
                                    size_hint=(None, None), size=(400, 100),
                                    pos=(Window.width / 2 - 200, Window.height - 300))
        self.add_widget(self.warning_label)

        # Schedule the removal of the warning message after 4 seconds
        Clock.schedule_once(self.remove_warning_message, 4)
        Clock.schedule_interval(self.deduce_points, 1)

    def remove_warning_message(self, dt):
        self.remove_widget(self.warning_label)

    def deduce_points(self, dt):
        if self.score > 0:
            self.score -= 10
            self.update_score(self.score)
        else:
            Clock.unschedule(self.deduce_points)

    def update_score(self, new_score):
        self.score = new_score
        self.score_display.update_score(new_score)

    def reflect_laser(self, vertical):
        # Calculate reflection based on the mirror's orientation
        if vertical:
            self.laser_velocity_x *= -1
        else:
            self.laser_velocity_y *= -1

        # Adjust laser rotation based on new velocity vector
        new_angle = math.atan2(self.laser_velocity_y, self.laser_velocity_x)
        self.laser.set_rotation(math.degrees(new_angle))

        # Optionally, move the laser slightly off the mirror to prevent immediate recollision
        offset_distance = 5 
        self.laser.laser_translation.x += offset_distance if vertical else 0
        self.laser.laser_translation.y += offset_distance if not vertical else 0

    def activate_bullet(self):
        if not self.bullet_active:
            self.bullet_active = True
            self.bullet_mass = 1.5
            self.score -= 100
            self.update_score(self.score)
            self.bullet_velocity = math.sqrt(400*2*self.powerbar.powerbar.size[0]/self.bullet_mass)
            self.bullet_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.bullet.set_pos(-self.cannon.size[0]/2 + cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), 
                                cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))
            self.bullet_velocity_x = self.bullet_velocity * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.bullet_velocity_y = self.bullet_velocity * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def activate_laser(self):
        if not self.laser_active:
            self.laser_active = True
            self.score -= 100
            self.update_score(self.score)
            self.laser_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.laser.set_pos_laser(0,0)
            self.laser.set_trans_laser(cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))
            self.laser.set_rotation(self.cannon_rotation.angle + 90)
            self.laser_velocity_x = 1500 * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.laser_velocity_y = 1500 * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def activate_cupcake(self):
        if not self.cupcake_active:
            self.score -= 200
            self.update_score(self.score)
            self.cupcake_active = True
            self.cupcake_mass = 3
            self.cupcake_velocity = math.sqrt(400*2*self.powerbar.powerbar.size[0]/self.cupcake_mass)
            self.cupcake_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.cupcake.set_pos(-self.cannon.size[0]/2 + cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), 
                              cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))

            # Calcola le componenti della velocità iniziale basate sull'angolo di inclinazione del cannone
            self.cupcake_velocity_x  = self.cupcake_velocity * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.cupcake_velocity_y = self.cupcake_velocity * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def _on_keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard.unbind(on_key_up=self._on_key_up)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        self.keyPressed.add(text)
        if keycode[1] == 'spacebar' and not self.laser_active:
            self.activate_bullet()
        if keycode[1] == "l" and not self.bullet_active:
            self.activate_laser()
        if keycode[1] == "k" and not self.cupcake_active:
            self.activate_cupcake()

    def _on_key_up(self, keyboard, keycode):
        text = keycode[1]
        if text in self.keyPressed:
            self.keyPressed.remove(text)

    def hide_enemy(self):
        self.music_button.stop_music()
        self.enemy.pos = (-1000, -1000)  # Move the enemy off-screen
        Clock.schedule_once(self.transition_to_intermediate, 1)
        global final_score_2
        final_score_2 = self.score

    def transition_to_intermediate(self, dt):
        # we adapt this for level 2 as we create a second intermediate screen with the updated score
        screen_manager = self.parent.manager
        screen_manager.current = 'intermediate2' 

    # Update function to handle game logic
    def update(self, dt):

        # In this level, the only mirror we have to check is the vertical one, 
        # so it's useless to handle collision for the horizontal mirror
        if not self.second_vertical_mirror.cooldown and collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.second_vertical_mirror.verticalmirror.pos, self.second_vertical_mirror.verticalmirror.size)):
            self.reflect_laser(vertical=True)
            self.second_vertical_mirror.start_cooldown()  # Start cooldown for vertical mirror

        # Check for collision with the front and rear part of the wormhole with the bullet
        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (self.wormhole.front.pos, self.wormhole.front.size)):
            self.teleport_bullet(self.bullet, self.wormhole.front, self.wormhole)
        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (self.wormhole.rear.pos, self.wormhole.rear.size)):
            self.teleport_bullet(self.bullet, self.wormhole.rear, self.wormhole)

        # The same for the cupcake
        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (self.wormhole.front.pos, self.wormhole.front.size)):
            self.teleport_bullet(self.cupcake, self.wormhole.front, self.wormhole)
        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (self.wormhole.rear.pos, self.wormhole.rear.size)):
            self.teleport_bullet(self.cupcake, self.wormhole.rear, self.wormhole)

        # Check for collision with rocks
        for rock in self.rocks[:]:
            if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (rock.rect.pos, rock.rect.size)):
                self.bullet_colliding = True
                self.rocks.remove(rock)
                self.remove_widget(rock)
                if self.hit_sound:
                    # make sure that the previous sound has stopped before playing a new one
                    self.hit_sound.stop()
                    self.hit_sound.play()
                break

        for rock in self.rocks[:]:  # Iterate over a copy of the rocks list
            if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (rock.rect.pos, rock.rect.size)):
                self.cupcake_colliding = True
                affected_rocks = [rock]  # Start with the initially collided rock

                # Find other rocks within the specified radius
                for other_rock in self.rocks[:]:  # Use a copy of the list for safe removal
                    # i had to use a higher radius for the cupcake to work properly, using 1000/50 didn't affect any other rocks 
                    # so it became pretty much useless
                    if other_rock is not rock and distance(rock.rect.pos, other_rock.rect.pos) <= 1000 / 25:
                        affected_rocks.append(other_rock)

                # Apply effects to all affected rocks
                for affected_rock in affected_rocks:
                    if affected_rock in self.rocks:  # Double-check to avoid errors
                        self.rocks.remove(affected_rock)
                        self.remove_widget(affected_rock)

                if self.hit_sound:
                    self.hit_sound.stop()
                    self.hit_sound.play()
                break  # Break after handling the cupcake collision

        # Check for collision with the enemy
        if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.enemy.pos, self.enemy.size)):
            self.laser_colliding = True
            self.hide_enemy()  # Hides the enemy

        # Check for bullet collision with the enemy
        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (self.enemy.pos, self.enemy.size)):
            self.bullet_colliding = True
            self.hide_enemy()  # Hides remove the enemy

        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (self.enemy.pos, self.enemy.size)):
            self.cupcake_colliding = True
            self.hide_enemy()  # Hides remove the enemy

        # Same as level 1
        if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y) ,self.laser.laser.size),(self.enemy.pos,self.enemy.size)):
            self.laser_colliding = True 

        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size),(self.enemy.pos, self.enemy.size)):
            self.bomb_colliding = True

        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size),(self.enemy.pos, self.enemy.size)):
            self.bullet_colliding = True

        if collides((self.player.pos, self.player.size), (self.enemy.pos, self.enemy.size)):
            self.is_colliding = True
        else:
            self.is_colliding = False         

        if not self.is_colliding:
            self.collision_left = False
            self.collision_right = False

        if self.is_colliding and (self.player.pos[0]<self.enemy.pos[0]):
            self.collision_right = True

        if self.is_colliding and (self.player.pos[0]>self.enemy.pos[0]):
            self.collision_left = True

        step_size = Window.width/8 * dt  
        rotation_speed = 45 * dt  

        # Movimento del 'player' e aggiornamento della posizione del 'cannon'
        if "a" in self.keyPressed and not self.collision_left  :
            new_x = max(self.player.pos[0] - step_size, 0)  # Non oltrepassare il bordo sinistro
            self.player.pos = (new_x, self.player.pos[1])

        if "d" in self.keyPressed and not self.collision_right:
            max_x = (Window.width/3) - self.player.size[0]
            new_x = min(self.player.pos[0] + step_size, max_x)  # Non oltrepassare il bordo destro
            self.player.pos = (new_x, self.player.pos[1])

        self.cannon_translation.x = self.player.pos[0] + self.player.size[0] / 2 
        self.cannon_translation.y = self.player.pos[1] + self.player.size[1] / 2

        if "w" in self.keyPressed:
            if self.cannon_rotation.angle + rotation_speed <= 90:  # limite superiore a +90 gradi
                self.cannon_rotation.angle += rotation_speed
        if "s" in self.keyPressed:
            if self.cannon_rotation.angle - rotation_speed >= -90:  # limite inferiore a -90 gradi
                self.cannon_rotation.angle -= rotation_speed

        if "p" in self.keyPressed and not self.bullet_active:
            if self.powerbar.powerbar.size[0] <= 600:
                self.powerbar.powerbar.size = (self.powerbar.powerbar.size[0] + 5, self.powerbar.powerbar.size[1])

        if "o" in self.keyPressed and not self.bullet_active:
            if self.powerbar.powerbar.size[0] >= 100:
                self.powerbar.powerbar.size = (self.powerbar.powerbar.size[0] - 5, self.powerbar.powerbar.size[1])

        if self.bullet_active:
            time_elapsed = Clock.get_boottime() - self.bullet_start_time
            x = self.bullet.ellipse.pos[0] + self.bullet_velocity_x * dt
            y = self.bullet.ellipse.pos[1] + self.bullet_velocity_y * dt - (0.5 * 9.8 * time_elapsed ** 2)
            self.bullet.set_pos(x, y)

            # Deactivate the bullet if it goes out of the window
            if x > Window.width or y < Window.height/15 or x < 0 or self.bullet_colliding:
                self.bullet_active = False
                self.bullet.set_pos(x, 3000)
                self.bullet_colliding = False

        if self.laser_active:

            x = self.laser.laser_translation.x + self.laser_velocity_x * dt
            y = self.laser.laser_translation.y + self.laser_velocity_y * dt
            self.laser.set_trans_laser(x, y)
            self.laser.laser_rotation = self.laser.laser_rotation

            if x > Window.width or y < Window.height/15 or y> Window.height or x < 0 or self.laser_colliding:
                self.laser_active = False
                self.laser.set_trans_laser(0, 3000)
                self.laser_colliding = False

        if self.cupcake_active:

            time_elapsed = Clock.get_boottime() - self.cupcake_start_time
            x = self.cupcake.ellipse.pos[0] + self.cupcake_velocity_x * dt
            y = self.cupcake.ellipse.pos[1] + self.cupcake_velocity_y * dt - (0.5 * 9.8 * time_elapsed ** 2)
            self.cupcake.set_pos(x, y)

            # DEACTIVATE BOMB if it goes out of the window
            if x > Window.width or y < Window.height/15 or x < 0 or self.cupcake_colliding:
                self.cupcake_active = False
                self.cupcake.set_pos(x, 3000)
                self.cupcake_colliding = False


class Level3GameWidget(RelativeLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        global final_score_2
        self.score = final_score_2
        global final_score_3
        Clock.schedule_once(self.start_deducing_points, 20)
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)
        self.is_colliding = False
        self.collision_left = False
        self.collision_right = False
        self.bullet_colliding = False
        self.laser_colliding = False
        self.cupcake_colliding = False

        # Load the sound file for the hit sound
        self.hit_sound = SoundLoader.load('./music/explosion.mp3')

        self.music_button = Music_button()
        self.add_widget(self.music_button)

        self.second_mirror_pos = (Window.width - 60, Window.height/4)
        self.second_vertical_mirror = VerticalMirror(pos=self.second_mirror_pos)
        self.add_widget(self.second_vertical_mirror)

        # Background image, the one that must come on before all the rest
        with self.canvas.before:
            self.background = Rectangle(source="./img/back_3.jpeg", pos=(0, 0), size=(Window.width, Window.height))

        with self.canvas:
            self.enemy = Rectangle(source="./img/tigro.png", pos=(Window.width/1.5, Window.height/18), size=(120, 200))

        with self.canvas:

            sizex = Window.width / 15
            sizey = Window.height/15
            posx = Window.width / 30
            posy = Window.height / 15
            Color(1, 1, 1, 1)

            PushMatrix()
            cannon_base_x = posx + sizex / 2
            cannon_base_y = posy + sizey / 2
            self.cannon_size = ((sizex/1.35)/4.5, sizey)
            self.cannon_translation = Translate(cannon_base_x, cannon_base_y)
            self.cannon_rotation = Rotate(origin=(0, self.cannon_size[1] / 4))

            self.cannon = Rectangle(source="./img/cannon_new.png", pos=(-self.cannon_size[0] / 2, self.cannon_size[1] / 4), size=self.cannon_size)
            PopMatrix()

            self.player = Rectangle(source="./img/tank.png", pos=(posx, posy), size=(sizex, sizey))

        self.bullet = Bullet()
        self.add_widget(self.bullet)

        self.cupcake = Cupcake()
        self.add_widget(self.cupcake)

        # Initialize the vertical and horizontal wall of perpetios
        self.perpetio = Perpetio()
        self.perpetios = []
        self.create_perpetio_wall()
        self.create_horizontal_wall(Window.height * 0.5, Window.width * 0.5, Window.width * 0.8)

        self.mirror = Mirror()
        self.add_widget(self.mirror)

        self.powerbar = PowerBar()
        self.add_widget(self.powerbar)   # spostare sopra per carro rgb

        self.laser = Laser()
        self.add_widget(self.laser)

        self.score_display = ScoreDisplay(self.score)
        self.add_widget(self.score_display)

        self.keyPressed = set()
        Clock.schedule_interval(self.update, 0)
        Clock.schedule_interval(self.laser.update_color, 0)

        self.bullet_active = False
        self.laser_active = False
        self.cupcake_active = False

    # I adapted the method we used for rocks before for the perpetios
    def create_perpetio_wall(self):
        num_perpetios = 9  
        perpetio_height = Window.height / 20 
        starting_y = (Window.height - num_perpetios * perpetio_height) / 2 
        perpetio_x = Window.width * 0.5

        starting_y -= 3.3 * perpetio_height

        # Generate positions for all perpetios: x is fixed, y is calculated based on the perpetio height
        perpetio_positions = [(perpetio_x, starting_y + i * perpetio_height) for i in range(num_perpetios)]

        # for each position, create a perpetio and add it to the list of perpetios (needed for further management)
        for position in perpetio_positions:
            perpetio = Perpetio(pos=position)
            self.add_widget(perpetio)
            self.perpetios.append(perpetio)

    def create_horizontal_wall(self, y_position, x_start, x_end):
        perpetio_width = Window.width / 20  # Calculate each rock's width based on the screen width
        perpetio_y = y_position  # Use the passed y_position for the wall's vertical position

        # Calculate the number of rocks based on the specified start and end points
        num_perpetios = int((x_end - x_start) / perpetio_width)

        # Generate positions for all rocks in the horizontal wall, starting from x_start
        perpetio_positions = [(x_start + i * perpetio_width, perpetio_y) for i in range(num_perpetios)]

        # Use map to apply add_rock to each position
        for position in perpetio_positions:
            perpetio = Perpetio(pos=position, size=(perpetio_width, perpetio_width))
            self.add_widget(perpetio)
            self.perpetios.append(perpetio)

    def start_deducing_points(self, dt):
        # Display warning message
        self.warning_label = Label(text="HURRY UP! From now on, you'll lose 10 points per second.",
                                    font_name = './Minecraft.ttf', font_size='20sp', color = (1, 0, 0, 1),
                                    size_hint=(None, None), size=(400, 100),
                                    pos=(Window.width / 2 - 200, Window.height - 300))
        self.add_widget(self.warning_label)
        # Schedule the removal of the warning message after 4 seconds
        Clock.schedule_once(self.remove_warning_message, 4)
        Clock.schedule_interval(self.deduce_points, 1)

    def remove_warning_message(self, dt):
        self.remove_widget(self.warning_label)

    def deduce_points(self, dt):
        if self.score > 0:
            self.score -= 10
            self.update_score(self.score)
        else:
            Clock.unschedule(self.deduce_points)

    def update_score(self, new_score):
        self.score = new_score
        self.score_display.update_score(new_score)

    def activate_bullet(self):
        if not self.bullet_active:
            self.bullet_active = True
            self.bullet_mass = 1.5
            self.score -= 100
            self.update_score(self.score)
            self.bullet_velocity = math.sqrt(400*2*self.powerbar.powerbar.size[0]/self.bullet_mass)
            self.bullet_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.bullet.set_pos(-self.cannon.size[0]/2 + cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))

            # Calcola le componenti della velocità iniziale basate sull'angolo di inclinazione del cannone
            self.bullet_velocity_x = self.bullet_velocity * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.bullet_velocity_y = self.bullet_velocity * math.sin(math.radians((self.cannon_rotation.angle)+90))
            print(cannon_tip_y)
            print(cannon_tip_x)
            print(self.player.pos[0])
            print(self.player.pos[1])

    def activate_laser(self):
        if not self.laser_active:
            self.laser_active = True
            self.score -= 100
            self.update_score(self.score)
            self.laser_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.laser.set_pos_laser(0,0)
            self.laser.set_trans_laser(cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))
            self.laser.set_rotation(self.cannon_rotation.angle + 90)
            self.laser_velocity_x = 1500 * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.laser_velocity_y = 1500 * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def activate_cupcake(self):
        if not self.cupcake_active:
            self.score -= 200
            self.update_score(self.score)
            self.cupcake_active = True
            self.cupcake_mass = 3
            self.cupcake_velocity = math.sqrt(400*2*self.powerbar.powerbar.size[0]/self.cupcake_mass)
            self.cupcake_start_time = Clock.get_boottime()
            cannon_tip_x = self.player.pos[0] + self.player.size[0]/2 
            cannon_tip_y = self.player.pos[1] + self.player.size[1]/2 + self.cannon.size[0]/2
            self.cupcake.set_pos(-self.cannon.size[0]/2 + cannon_tip_x + self.cannon.size[1]* math.cos(math.radians((self.cannon_rotation.angle)+90)), 
                              cannon_tip_y+ self.cannon.size[1]* math.sin(math.radians((self.cannon_rotation.angle)+90)))
            self.cupcake_velocity_x  = self.cupcake_velocity * math.cos(math.radians((self.cannon_rotation.angle)+90))
            self.cupcake_velocity_y = self.cupcake_velocity * math.sin(math.radians((self.cannon_rotation.angle)+90))

    def _on_keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard.unbind(on_key_up=self._on_key_up)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        self.keyPressed.add(text)
        if keycode[1] == 'spacebar' and not self.laser_active:
            self.activate_bullet()
        if keycode[1] == "l" and not self.bullet_active:
            self.activate_laser()
        if keycode[1] == "k" and not self.cupcake_active:
            self.activate_cupcake()

    def _on_key_up(self, keyboard, keycode):
        text = keycode[1]
        if text in self.keyPressed:
            self.keyPressed.remove(text)

    def hide_enemy(self):
        self.music_button.stop_music()
        self.enemy.pos = (-1000, -1000)  # Move the enemy off-screen
        Clock.schedule_once(self.transition_to_leaderboard, 1)
        global final_score_3
        final_score_3 = self.score

    def transition_to_leaderboard(self, dt):
        screen_manager = self.parent.manager
        screen_manager.current = 'leaderboard' 

    def reflect_laser(self, vertical):
        # Calculate reflection based on the mirror's orientation
        if vertical:
            self.laser_velocity_x *= -1
        else:
            self.laser_velocity_y *= -1

        # Adjust laser rotation based on new velocity vector
        new_angle = math.atan2(self.laser_velocity_y, self.laser_velocity_x)
        self.laser.set_rotation(math.degrees(new_angle))
        
        # Optionally, move the laser slightly off the mirror to prevent immediate recollision
        offset_distance = 5  # Adjust as needed
        self.laser.laser_translation.x += offset_distance if vertical else 0
        self.laser.laser_translation.y += offset_distance if not vertical else 0


    # Update function to handle game logic
    def update(self, dt):

        # same as before, we only have to check for the vertical and horizontal mirror
        if not self.mirror.cooldown and collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.mirror.mirror.pos, self.mirror.mirror.size)):
            self.reflect_laser(vertical=False)
            self.mirror.start_cooldown()  # Start cooldown for horizontal mirror

        if not self.second_vertical_mirror.cooldown and collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.second_vertical_mirror.verticalmirror.pos, self.second_vertical_mirror.verticalmirror.size)):
            self.reflect_laser(vertical=True)
            self.second_vertical_mirror.start_cooldown()  # Start cooldown for vertical mirror

        # check for collisions with the perpetios stacked in the walls, the same way we used to do for the rocks
        for perpetio in self.perpetios:
            if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (perpetio.rect.pos, perpetio.rect.size)):
                # now perpetios aren't removed, but bullet is
                self.bullet_active = False
                self.bullet_colliding = True
                self.bullet.set_pos(self.bullet.ellipse.pos[0], 3000)

            # same for lasers and cupcakes as well
            if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size) ,(perpetio.rect.pos, perpetio.rect.size)):
                self.laser_active = False
                self.laser_colliding = True
                self.laser.laser_translation.x = 0
                self.laser.laser_translation.y = 3000

            if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (perpetio.rect.pos, perpetio.rect.size)):
                self.cupcake_active = False
                self.cupcake_colliding = True
                self.cupcake.set_pos(self.cupcake.ellipse.pos[0], 3000)

        # Check for collision with the mirror
        if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y), self.laser.laser.size), (self.enemy.pos, self.enemy.size)):
            print('laser colliding with enemy')
            self.laser_colliding = True
            self.hide_enemy()  # Hides the enemy

        # Check for bullet collision with the enemy
        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size), (self.enemy.pos, self.enemy.size)):
            print('bullet colliding with enemy')
            self.bullet_colliding = True
            self.hide_enemy()  # Hides remove the enemy

        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size), (self.enemy.pos, self.enemy.size)):
            self.cupcake_colliding = True
            self.hide_enemy()  # Hides remove the enemy

        if collides(((self.laser.laser_translation.x, self.laser.laser_translation.y) ,self.laser.laser.size),(self.enemy.pos,self.enemy.size)):
            self.laser_colliding = True 

        if collides((self.bullet.ellipse.pos, self.bullet.ellipse.size),(self.enemy.pos, self.enemy.size)):
            self.bullet_colliding = True

        if collides((self.cupcake.ellipse.pos, self.cupcake.ellipse.size),(self.enemy.pos, self.enemy.size)):
            self.cupcake_colliding = True

        if collides((self.player.pos, self.player.size), (self.enemy.pos, self.enemy.size)):
            self.is_colliding = True
        else:
            self.is_colliding = False         

        if not self.is_colliding:
            self.collision_left = False
            self.collision_right = False

        if self.is_colliding and (self.player.pos[0]<self.enemy.pos[0]):
            self.collision_right = True

        if self.is_colliding and (self.player.pos[0]>self.enemy.pos[0]):
            self.collision_left = True

        step_size = Window.width/8 * dt
        rotation_speed = 45 * dt

        if "a" in self.keyPressed and not self.collision_left:
            new_x = max(self.player.pos[0] - step_size, 0)
            self.player.pos = (new_x, self.player.pos[1])

        if "d" in self.keyPressed and not self.collision_right:
            max_x = (Window.width/3) - self.player.size[0]
            new_x = min(self.player.pos[0] + step_size, max_x)
            self.player.pos = (new_x, self.player.pos[1])

        self.cannon_translation.x = self.player.pos[0] + self.player.size[0] / 2 
        self.cannon_translation.y = self.player.pos[1] + self.player.size[1] / 2

        if "w" in self.keyPressed:
            if self.cannon_rotation.angle + rotation_speed <= 90:
                self.cannon_rotation.angle += rotation_speed
        if "s" in self.keyPressed:
            if self.cannon_rotation.angle - rotation_speed >= -90:
                self.cannon_rotation.angle -= rotation_speed

        if "p" in self.keyPressed and not self.bullet_active:
            if self.powerbar.powerbar.size[0] <= 600:
                self.powerbar.powerbar.size = (self.powerbar.powerbar.size[0] + 5, self.powerbar.powerbar.size[1])

        if "o" in self.keyPressed and not self.bullet_active:
            if self.powerbar.powerbar.size[0] >= 100:
                self.powerbar.powerbar.size = (self.powerbar.powerbar.size[0] - 5, self.powerbar.powerbar.size[1])

        if self.bullet_active:

            time_elapsed = Clock.get_boottime() - self.bullet_start_time
            x = self.bullet.ellipse.pos[0] + self.bullet_velocity_x * dt
            y = self.bullet.ellipse.pos[1] + self.bullet_velocity_y * dt - (0.5 * 9.8 * time_elapsed ** 2)
            self.bullet.set_pos(x, y)

            # Deactivate the bullet if it goes out of the window
            if x > Window.width or y < Window.height/15 or x < 0 or self.bullet_colliding:
                self.bullet_active = False
                self.bullet.set_pos(x, 3000)
                self.bullet_colliding = False

        if self.laser_active:

            x = self.laser.laser_translation.x + self.laser_velocity_x * dt
            y = self.laser.laser_translation.y + self.laser_velocity_y * dt
            self.laser.set_trans_laser(x, y)
            self.laser.laser_rotation = self.laser.laser_rotation

            if x > Window.width or y < Window.height/15 or y> Window.height or x < 0 or self.laser_colliding:
                self.laser_active = False
                self.laser.set_trans_laser(0, 3000)
                self.laser_colliding = False

        if self.cupcake_active:

            time_elapsed = Clock.get_boottime() - self.cupcake_start_time
            x = self.cupcake.ellipse.pos[0] + self.cupcake_velocity_x * dt
            y = self.cupcake.ellipse.pos[1] + self.cupcake_velocity_y * dt - (0.5 * 9.8 * time_elapsed ** 2)
            self.cupcake.set_pos(x, y)

            # DEACTIVATE BOMB if it goes out of the window
            if x > Window.width or y < Window.height/15 or x < 0 or self.cupcake_colliding:
                self.cupcake_active = False
                self.cupcake.set_pos(x, 3000)
                self.cupcake_colliding = False


class StoryScreen(Screen):
    # Displayer for the two story images. The user can go to the next image by clicking on the 'Next' button
    def on_enter(self, *args):
        self.story_images = ['./img/story1.jpg', './img/story2.jpg']
        self.current_image = 0
        self.display_story()

    def display_story(self):
        self.clear_widgets()  # Clear the screen for the new image and button
        if self.current_image < len(self.story_images):
            img = Image(source=self.story_images[self.current_image])
            self.add_widget(img)  # Display the current image

            # Create a 'Next' button to go to the next image
            next_button = ImageButton(source='./img/next.jpeg', size_hint=(0.1, 0.1), pos_hint={'center_x': 0.9, 'bottom': 0.4})
            next_button.bind(on_press=self.next_image)
            self.add_widget(next_button)  # Add the button to the screen
        else:
            self.manager.current = 'levelspage'  # Go to level1 if it's the last image

    def next_image(self, instance):
        self.current_image += 1  # Increment the image index
        self.display_story()  # Call display_story again to update the image


class HomePage(Screen):
    # Home page with a 'Start' button to go to the levels page
    def on_enter(self, *args):
        self.add_widget(Image(source='./img/home_back.jpeg', allow_stretch=True, keep_ratio=False))
        start_img = './img/start.png'
        start_button = ImageButton(source=start_img, size_hint=(0.3, 0.18), pos_hint={'center_x': 0.5, 'center_y': 0.1})
        start_button.bind(on_press=self.goto_levels)
        self.add_widget(start_button)
        self.options_button = OptionsButton()
        self.add_widget(self.options_button)

    def goto_levels(self, instance):
        self.manager.current = 'story'


class ImageButton(ButtonBehavior, Image):
    # needed to implement image buttons, as they aren't built-in in Kivy
    pass


class Level1(Screen):
    def on_enter(self, *args):
        # Here I call the game widget for the first level
        super(Level1, self).on_enter(*args)
        self.game_widget = Level1GameWidget()
        self.add_widget(self.game_widget)

        # add options button
        self.options_button = OptionsButton()
        self.add_widget(self.options_button)


class Level2(Screen):
    def on_enter(self, *args):
        # Here I call the game widget for level 2 and the options button
        super(Level2, self).on_enter(*args)
        self.game_widget = Level2GameWidget()
        self.add_widget(self.game_widget)
        self.options_button = OptionsButton()
        self.add_widget(self.options_button)   


class Level3(Screen):
    def on_enter(self, *args):
        # Here I call the game widget for lev. 3 and the options button
        super(Level3, self).on_enter(*args)
        self.game_widget = Level3GameWidget()
        self.add_widget(self.game_widget)
        self.options_button = OptionsButton()
        self.add_widget(self.options_button)


class IntermediateScreen1(Screen):
    def on_enter(self, *args):
        global final_score_1
        self.add_widget(Image(source='./img/lvclear.png', allow_stretch=True, keep_ratio=False))

        # Display the final score of the player
        self.score_display = ScoreBanner(score=final_score_1)
        self.add_widget(self.score_display)

        # Create a 'Next' button to go to the next level
        next_level_btn = ImageButton(source='./img/next.jpeg', size_hint=(0.5, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.1})
        next_level_btn.bind(on_press=self.go_to_next_level)
        self.add_widget(next_level_btn)

        # Create a 'Back' button to go back to the levels page
        back_btn = ImageButton(source='./img/backtolev.png', size_hint=(0.6, 0.3), pos_hint={'center_x': 0.5, 'center_y': 0.25})
        back_btn.bind(on_press=self.go_back_to_levels)
        self.add_widget(back_btn)

    def go_back_to_levels(self, instance):
        # move to the levels page
        self.manager.current = 'levelspage'

    def go_to_next_level(self, instance):
        self.manager.current = 'level2'
        pass


class IntermediateScreen2(Screen):
    # same as before, but for the second level to move to the third
    def on_enter(self, *args):
        global final_score_2
        self.add_widget(Image(source='./img/lvclear.png', allow_stretch=True, keep_ratio=False))

        self.score_display = ScoreBanner(score=final_score_2)
        self.add_widget(self.score_display)

        next_level_btn = ImageButton(source='./img/next.jpeg', size_hint=(0.5, 0.1), pos_hint={'center_x': 0.5, 'center_y': 0.1})
        next_level_btn.bind(on_press=self.go_to_next_level)
        self.add_widget(next_level_btn)
        
        back_btn = ImageButton(source='./img/backtolev.png', size_hint=(0.6, 0.3), pos_hint={'center_x': 0.5, 'center_y': 0.25})
        back_btn.bind(on_press=self.go_back_to_levels)
        self.add_widget(back_btn)

    def go_back_to_levels(self, instance):
        self.manager.current = 'levelspage'

    def go_to_next_level(self, instance):
        # Implement logic to go to the next level
        self.manager.current = 'level3'
        pass


class LevelsPage(Screen):
    def on_enter(self, *args):
        super(LevelsPage, self).on_enter(*args)
        self.clear_widgets()  # Clear existing widgets

        bg_image = Image(source='./img/background_levela.jpg', allow_stretch=True, keep_ratio=False)
        self.add_widget(bg_image)

        self.options_button = OptionsButton()
        self.add_widget(self.options_button)

        level_images = ['./img/icon_1.png', './img/icon_2.png', './img/icon_3.png']
        positions = [(0.15, 0.75), (0.5, 0.75), (0.85, 0.15)]  # Positions of the level images

        # Create a image button for each level, with a fixed size and the positions we defined above
        for i, (img, pos) in enumerate(zip(level_images, positions), start=1):
            level_button = ImageButton(source=img, size_hint=(0.2, 0.2), pos_hint={'center_x': pos[0], 'center_y': pos[1]})
            level_button.bind(on_press=self.goto_level)
            self.add_widget(level_button)

    def goto_level(self, instance):
        # Extract the level number from the filename (e.g., 'icon_1.png')
        level_number = instance.source.split('_')[-1].split('.')[0]
        level_number = int(level_number)

        # Check conditions before navigating
        if level_number == 1:
            self.manager.current = 'level1'
        elif level_number == 2:
            # Check if the player has completed the previous level
            if 'final_score_1' in globals():
                self.manager.current = 'level2'
            else:
                self.show_popup()
        elif level_number == 3:
            # by checking final_score_2, you automatically check for final_score_1
            if 'final_score_2' in globals():
                self.manager.current = 'level3'
            else:
                self.show_popup()

    def show_popup(self):
        # Create a popup to inform the player that they need to complete the previous level, 
        # in the scenario where they click a locked level
        root_layout = BoxLayout(orientation='vertical')
        with root_layout.canvas.before:
            Color(0.949, 0.718, 0.808)  # pink background color
            self.rect = Rectangle(size=root_layout.size, pos=root_layout.pos)

        # Update the rectangle size and position on layout updates
        def update_rect(instance, value):
            self.rect.pos = instance.pos
            self.rect.size = instance.size
        root_layout.bind(pos=update_rect, size=update_rect)

        # Custom title label
        title_label = Label(text='Level Locked', font_size='30sp', 
                            font_name='./Minecraft.ttf', 
                            size_hint_y=None, height=50, color=(1, 1, 1, 1))

        # message for the player, specifying that they need to complete the previous level
        label = Label(text="You need to complete the previous level to unlock this one!",
                           font_size='20sp', 
                            font_name='./Minecraft.ttf', 
                            size_hint= (1, None), height=400, color=(1, 1, 1, 1),
                            halign='center', valign='center', text_size=(400, None))

        root_layout.add_widget(title_label)
        root_layout.add_widget(label)

        # Create a popup with the layout
        warning_popup = Popup(title='', content=root_layout, size_hint=(None, None), size=(500, 400), 
                           background_color=[0, 0, 0, 0])
        warning_popup.open()


class Leaderboard(Screen):
    def on_enter(self, *args):
        # when the screen is entered, we're shown the popup. after we do what it's asking us, we update and display the leaderboard
        self.show_name_popup()

    def show_name_popup(self):
        # Create a popup to ask the player for their name to save the score in the leaderboard
        content = BoxLayout(orientation='vertical', spacing=10)
        with content.canvas.before:
            Color(0.961, 0.761, 0.851)
            self.rect = Rectangle(size=content.size, pos=content.pos)

        content.bind(size=self._update_rect, pos=self._update_rect)

        # Create a TextInput for the player to enter their name, and a button to confirm it
        self.name_input = TextInput(hint_text='Enter your name', font_name='./Minecraft.ttf', size_hint_y=None, height=30)
        content.add_widget(self.name_input)
        confirm_btn = ImageButton(source='./img/confirm.png', on_press=self.on_name_confirm, size_hint_y=None, height=40)
        content.add_widget(confirm_btn)

        # Create a popup with the content
        self.popup = Popup(title='', content=content, size_hint=(None, None), size=(400, 200))
        self.popup.open()

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def on_name_confirm(self, instance):
        self.popup.dismiss()
        player_name = self.name_input.text.strip() # Get the player's name
        final_score_3 = globals().get('final_score_3', 0)  # Assuming final_score_3 is a global variable
        DataHandler.update_leaderboard(player_name, final_score_3) # update the leaderboard at name confirmation
        self.display_leaderboard()  # Refresh the leaderboard display

    def display_leaderboard(self):
        self.clear_widgets()  # Clear existing widgets on the leaderboard screen
        title_image = Image(source='./img/titolo.jpeg', pos=(0, Window.height - 460), size=(Window.width, 80))
        self.add_widget(title_image)

        # Create a ScrollView, the size respects the presence of a title image
        scroll_view = ScrollView(size_hint=(1, None), size=(Window.width, Window.height - 150))
        scroll_view.bar_width = 10
        scroll_view.scroll_type = ['bars', 'content']
        
        # Create a BoxLayout for the names
        names_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        with names_layout.canvas.before:
            Color(0.95686, 0.76863, 0.84706)
            self.rect = Rectangle(size=names_layout.size, pos=names_layout.pos)
        
        # Update the rectangle size and position when the layout changes
        names_layout.bind(minimum_height=names_layout.setter('height'))
        names_layout.bind(size=self._update_rect, pos=self._update_rect)

        leaderboard = DataHandler.read_leaderboard()
        leaderboard = [(name, int(score)) for name, score in leaderboard]  # Convert score to int
        leaderboard.sort(key=lambda x: x[1], reverse=True)  # Sort by score in DESCENDING order (higher the score, higher the position)
        for name, score in leaderboard:
            # Create a label for each name and score and add them as widgets to the BoxLayout
            name_label = Label(text=f'{name}: {score}', font_name='./Minecraft.ttf', size_hint_y=None, height=50)
            names_layout.add_widget(name_label)
        
        # Add the BoxLayout to the ScrollView
        scroll_view.add_widget(names_layout)
        
        # Add the ScrollView to the screen
        self.add_widget(scroll_view)
        
        # Add the back button, that will take the player back to the homepage
        back_btn = ImageButton(source='./img/home.png', size_hint=(None, None), size=(100, 50), pos_hint={'right': 0.9, 'y': 0.1}, on_press=self.go_back)
        self.add_widget(back_btn)

    def go_back(self, instance):
        self.manager.transition.direction = 'right'
        self.manager.current = 'homepage'


class SugarWarsApp(App):
    def build(self):
        # Create the screen manager and add the screens
        sm = ScreenManager()
        sm.add_widget(HomePage(name='homepage'))
        sm.add_widget(LevelsPage(name='levelspage'))
        sm.add_widget(StoryScreen(name='story'))
        sm.add_widget(Level1(name='level1'))
        sm.add_widget(IntermediateScreen1(name='intermediate'))
        sm.add_widget(Level2(name='level2'))
        sm.add_widget(IntermediateScreen2(name='intermediate2'))
        sm.add_widget(Level3(name='level3'))
        sm.add_widget(Leaderboard(name='leaderboard'))
        return sm


if __name__ == "__main__":
    app = SugarWarsApp()
    app.run()
