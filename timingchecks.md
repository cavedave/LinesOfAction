Befopre gameboard coying Issue
harness timing: 20 games, play_one_game sum 13.748s (mean 0.687s/game, min 0.675s, max 0.701s; full batch wall 13.750s incl. bot setup)
{
  "a_wins": 10,
  "b_wins": 10,
  "draws": 0,
  "timing": {
    "total_s": 13.747992,
    "batch_wall_s": 13.750234,
    "mean_s": 0.6874,
    "min_s": 0.675074,
    "max_s": 0.700515,
    "per_game_s": [
      0.675078,
      0.676389,
      0.675074,
      0.676776,
      0.683151,
      0.680312,
      0.681595,
      0.682823,
      0.687787,
      0.686646,
      0.687257,
      0.689728,
      0.692105,
      0.694726,
      0.69283,
      0.695097,
      0.696902,
      0.695447,
      0.700515,
      0.697754
    ]
  }


  After gameboard copy fix

  python -m harness --a minimax_d3 --b minimax_d3 --games 20 --dim 6

  harness timing: 20 games, play_one_game sum 13.751s (mean 0.688s/game, min 0.665s, max 0.730s; full batch wall 13.754s incl. bot setup)
{
  "a_wins": 10,
  "b_wins": 10,
  "draws": 0,
  "timing": {
    "total_s": 13.751254,
    "batch_wall_s": 13.753926,
    "mean_s": 0.687563,
    "min_s": 0.665037,
    "max_s": 0.730364,
    "per_game_s": [
      0.667564,
      0.665037,
      0.668317,
      0.674976,
      0.672907,
      0.673353,
      0.674576,
      0.675694,
      0.730364,
      0.684371,
      0.681488,
      0.686838,
      0.692827,
      0.693114,
      0.697211,
      0.698424,
      0.698464,
      0.698166,
      0.691104,
      0.726459
    ]
  }
}


D4 versions

harness timing: 20 games, play_one_game sum 103.143s (mean 5.157s/game, min 4.903s, max 5.448s; full batch wall 103.147s incl. bot setup)
{
  "a_wins": 10,
  "b_wins": 10,
  "draws": 0,
  "timing": {
    "total_s": 103.143406,
    "batch_wall_s": 103.146519,
    "mean_s": 5.15717,
    "min_s": 4.903306,
    "max_s": 5.448306,
    "per_game_s": [
      4.903306,
      4.980369,
      5.04982,
      5.129031,
      5.298614,
      5.095025,
      5.092471,
      5.07903,
      5.129914,
      5.448306,
      5.442943,
      5.149508,
      5.16269,
      5.122935,
      5.187956,
      5.20462,
      5.200847,
      5.205464,
      5.132373,
      5.128184
    ]
  }
}

D5 version 

python -m harness --a minimax_d4 --b minimax_d5 --games 1 --dim 6

pygame 2.6.1 (SDL 2.28.4, Python 3.13.7)
Hello from the pygame community. https://www.pygame.org/contribute.html
harness timing: 1 games, play_one_game sum 21.367s (mean 21.367s/game, min 21.367s, max 21.367s; full batch wall 21.368s incl. bot setup)
{
  "a_wins": 0,
  "b_wins": 1,
  "draws": 0,
  "timing": {
    "total_s": 21.367387,
    "batch_wall_s": 21.367565,
    "mean_s": 21.367387,
    "min_s": 21.367387,
    "max_s": 21.367387,
    "per_game_s": [
      21.367387
    ]
  }

  d5 with 8*8 board 

  Hello from the pygame community. https://www.pygame.org/contribute.html
harness timing: 1 games, play_one_game sum 258.932s (mean 258.932s/game, min 258.932s, max 258.932s; full batch wall 258.932s incl. bot setup)
{
  "a_wins": 0,
  "b_wins": 1,
  "draws": 0,
  "timing": {
    "total_s": 258.931755,
    "batch_wall_s": 258.931833,
    "mean_s": 258.931755,
    "min_s": 258.931755,
    "max_s": 258.931755,
    "per_game_s": [
      258.931755
    ]
  }
}

***********

