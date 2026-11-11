"""Words and sentences used to build practice lines.

The generator only picks entries made entirely of keys the child has
learned, so a big varied bank means more variety at every stage. Sentences
are written with normal capitals and punctuation; before Shift and the
punctuation keys are taught they're lowercased and the full stops and commas
dropped.
"""

WORDS = tuple(sorted(set("""
a add ads aid aide ail all alas as ask asks dad dads dash fad fads fall falls
flag flags flash flask gal gas glad glass had half hall hash has jag lad lads
lag lash lass sad saga salad shall slash

aid die dies dig digs dish fade feed feel feels file fish flake glide hid hide
hike idea ideas jail jade keg kid kids lake leaf leak led leg legs lid lie like
life sea seal seed see seek she shed shelf side ski skid sled slide sail said
ease easel else egg eggs feast field fig fill flies gale geese hail heal heel
hike held hill kegs lead lilies lea like liked aside ahead

are art dart dear deer desk dress drag dragon draw drip dried fair far farm
fire fired free fresh frog fur her here hurt jar jug kite lard rid ride rides
road rug rule rush sad sir sure user use used dust duke fuel full gum hug huge
hut lure rug rude rush sugar surf

tea tree treat trip true tiger tart test the they this that their there these
to toe toes too top tired ship hat heat hit hot jet kit let lit pet rat sat
set sit tag tail tall tea teeth toast today yard yes yet yellow you your
youth day days easy eye eyes fly frosty gray happy hay key lady lazy play
pray ray say silly stay story toy toys try yak yay yo yoyo

wait walk wall warm wash water way we west wet white wide wife will wish with
wolf wood word work world hello yellow how low owl own row slow snow show
float flower food fool foot for forest fork go goat gold good got hold hole
home hope hot joke look lot lots of off oil old or our out over owl road rose
soft sold store stood tooth wood world old show

quiet quilt quit quick quite queen quest quote pea peas pear pet pie pig pigs
pillow pink pirate pit pool pop pot purple put paper party pup puppy pupil
pizza apple happy hop hope jump keep kept leap lip lips map mop pal pass
plate please plus pod poke pole pose post pots pour proud

van very vase vet visit love live give have five gave dive drive move oven
over river seven silver save wave cave vote violin
man map mat me milk mind mom mud mug must my mum am arm farm from game
him home jam made make mama more moon most much name same some summer swim
time from storm drum gum lamp camp
bag bat bed bee best big bike bird boat book box bug bus but by baby back
bake ball band bath bear beach bell belt bit blue bob bone bowl brave bread
bright brown bubble bunny bush tub rub web cab crab rib job grab table
and an any can fan fin fun hand hen in land man nap net new nice night nine
no nose not now on one pan pen pin ran run sand sun ten tin win wind wing
cake call came can cap car card cat cats cold cook cool cow cup cut cute
city clap class clock cloud coat cocoa cream cub dance face ice nice race
rice duck sock rock pick kick lick neck back black clock snack track
fox box six mix fix wax ax taxi next
zoo zip zero zebra lazy jazz fizz buzz prize size freeze maze puzzle
""".split())))

NAMES = ("Ava", "Ben", "Cara", "Dan", "Eli", "Finn", "Gus", "Hana", "Ivy",
         "Jack", "Kate", "Liam", "Lulu", "Mia", "Noah", "Omar", "Pip", "Quinn",
         "Ruby", "Sam", "Tom", "Uma", "Vic", "Will", "Xena", "Yara", "Zoe",
         "Jo", "Kip", "Leo", "Nell", "Olly", "Hugo", "Iris", "Yuki", "Max",
         "Dora", "Fred", "Rosa", "Tess", "Walt", "Ella", "Gail", "Ada", "Bea",
         "Cal", "Vera", "Zack", "Kai", "Lily", "Nia")

SENTENCES = (
    # Mostly home row and top row letters, so the top row lesson has plenty.
    "The dog is quite happy.",
    "A red kite flew so high.",
    "She said the tea is hot.",
    "It is a hot day at the sea.",
    "The frog sat at the pool.",
    "We sit together at the lake.",
    "The sheep eat the grass.",
    "A tiger is asleep here.",
    "It is too hot for the goat.",
    "The kids ride a red sled.",
    "What a great dog.",
    "Please pass the salt.",
    "A giraffe is so tall.",
    "The pirate hid the gold.",
    "Our sheep is fluffy.",
    "They ate pie at the party.",
    "We hope it is sunny.",
    "Dad is fixing the tap.",
    "I like to read a story.",
    "The puppy dug up a sock.",
    "Look at the white goose.",
    "Let us eat a pear.",
    "Wait for the yellow light.",
    "The water is too deep.",
    "Your hat is so pretty.",
    "A puppy is a good pet.",
    "I hope it is your party.",
    "The fish sits at the top.",
    "We had toast at the fair.",
    # General sentences once the bottom row is learned.
    "The cat sat on the mat.",
    "My dog likes to dig in the garden.",
    "We went to the beach.",
    "The sun is warm and bright.",
    "I can ride my bike.",
    "Mum made pancakes for breakfast.",
    "A little bird sang in the tree.",
    "The moon is big tonight.",
    "My friend has a new puppy.",
    "We baked cookies today.",
    "The fox jumped over the log.",
    "Zoe likes to swim in the lake.",
    "The bus is red and very big.",
    "I put my socks in the box.",
    "A brown bear ate some honey.",
    "The baby is having a nap.",
    "We can play in the snow.",
    "My teddy bear is soft.",
    "The ducks swim in the pond.",
    "Ben has a blue kite.",
    "The clock says it is time for bed.",
    "I love to paint pictures.",
    "The wind blew my hat away.",
    "We grow carrots and beans.",
    "Max has six crayons.",
    "The zebra has black and white stripes.",
    "Mia found a shell on the sand.",
    "The owl hoots at night.",
    "A frog can jump very far.",
    "Grandma knits warm scarves.",
    "We read a book about space.",
    "My cat naps in the sun.",
    "Sam and Ava built a sandcastle.",
    "The train goes very fast.",
    "Liam can whistle a tune.",
    "Cows eat grass in the field.",
    "My lunch box is green.",
    "Pip, Max and Zoe went camping.",
    "It was cold, so we wore coats.",
    "First we ate, then we played.",
    "On rainy days, we read books.",
    # Apostrophes and question marks.
    "Can you see the rainbow?",
    "Let's play a game.",
    "I'm going to the park.",
    "Where is my red sock?",
    "It's time to go home.",
    "Do you like ice cream?",
    "Don't forget your hat.",
    "What is your name?",
    "We're having fun today.",
    "Who ate the last cookie?",
    "That's a big dog.",
    "Is it your turn yet?",
    "I can't find my shoe.",
    "How old is your cat?",
    "She's my best friend.",
    "Are we there yet?",
    # Numbers.
    "I have 2 cats and 1 dog.",
    "There are 7 days in a week.",
    "We counted 12 ducks at the pond.",
    "My sister is 9 years old.",
    "The bus comes at 8 every day.",
    "A spider has 8 legs.",
    "There are 30 kids in my class.",
    "I read 5 books this month.",
    "We need 4 eggs for the cake.",
    "My house is number 26.",
    "It is 10 steps to the gate.",
    "The year has 12 months.",
    "Grandpa is 70 years old.",
    "I scored 3 goals today.",
    "We picked 15 apples.",
    "Can you count to 100?",
    "There are 60 minutes in an hour.",
    "My team won 4 to 2.",
    # Punctuation lesson: ! " - and :
    "What a big splash!",
    "Look out for the bee!",
    "We won the game!",
    "Hooray, it is snowing!",
    "Wow, what a tall tower!",
    "Stop, the light is red!",
    'Mum said, "Time for bed."',
    '"Can I play?" asked Ben.',
    '"Look at me!" said the frog.',
    'Dad said, "Let us go to the park."',
    '"I like jam," said Zoe.',
    '"Is it time yet?" asked Max.',
    "My dog is two years old and well-behaved.",
    "We ate ice-cream at the seaside.",
    "Her bike is bright blue-green.",
    "The sixty-two buses go to town.",
    "Pack three things: a hat, a map and a snack.",
    "Here is the plan: eat, play, then sleep.",
    "The bus leaves at 9:15 each day.",
    "Shopping list: eggs, milk and jam.",
)

STORIES = {
    "kite": (
        "The Runaway Kite",
        "Pip had a red kite with a long, wiggly tail. One windy day it "
        "pulled free and flew over the tall trees. Pip ran and ran until "
        "she found it stuck in a big muddy puddle. She laughed, washed it "
        "off and flew it again.",
    ),
    "snail": (
        "Slow and Steady",
        "Sid the snail wanted to see the top of the hill. The rabbits "
        "hopped past him and the birds flew over him. Sid kept going, "
        "one small step at a time. When the sun went down, Sid was at the "
        "top, and the view was wonderful.",
    ),
    "pancakes": (
        "Pancake Morning",
        "On Saturday, Max and his dad made pancakes. They cracked 3 eggs "
        "and mixed in milk and flour. Max flipped the first pancake so high "
        "that it landed on the dog. The dog wagged his tail. Max made 12 "
        "more, and nobody got wet this time.",
    ),
    "stars": (
        "The Night Sky",
        "Ava and her grandma sat outside on a warm night. They looked up "
        "and counted the stars. Grandma pointed at a bright one and said "
        "it was a planet. Ava wished on a shooting star. She won't tell "
        "anyone what she wished for.",
    ),
    # These come after Punctuation Pros, so they can use ! " - and :
    "puddles": (
        "Puddle Day",
        "It rained all morning. When it stopped, Leo put on his yellow boots "
        'and ran outside. "Look at this one!" he shouted, and jumped into the '
        "biggest puddle on the street. Splash! Mum laughed and said, "
        '"Now your socks are wet too."',
    ),
    "garden": (
        "The Tiny Garden",
        "Nia planted five seeds in a pot by the window. She gave them water "
        "every day and sang to them. After two weeks, a little green shoot "
        "poked out of the soil. Then another and another! By the summer, Nia "
        "had a pot full of bright, sweet-smelling flowers.",
    ),
    "robot": (
        "Bolt the Robot",
        "Bolt was a small robot with one job: to tidy the toy box. Every night "
        "he picked up the blocks, the cars and the teddy bears. One night he "
        'found a lost marble under the bed. "Got you!" he beeped. The next '
        "morning, Rosa found it on her pillow.",
    ),
    "sock": (
        "The Missing Sock",
        "Every week, one of Gus's socks went missing. He looked under the bed, "
        "in the bath and behind the sofa. Then he saw the cat curled up in her "
        "basket. Under her was a cosy nest made of socks: red ones, blue ones "
        'and one with stripes. "Well," said Gus, "at least they are warm."',
    ),
}
