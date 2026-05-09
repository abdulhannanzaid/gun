# 🔥 FIREBALL

A fast-paced multiplayer game where you must pass the burning fireball before it explodes!

## 🎮 Game Overview

In **FIREBALL**, you're thrown into an arena with AI opponents, all competing to stay alive. The fireball is constantly changing hands, and it burns hotter every second it's passed around. Hold it too long and it explodes—eliminating you from the game. The last player standing wins!

## 🕹️ Controls

### Movement
- **WASD** or **Arrow Keys** — Move your character around the arena
- Avoid walls and obstacles to survive longer

### Throwing the Fireball
- **Click on an opponent** — Throw the fireball at them
- You can only throw when you hold the ball
- Try to pass it to nearby players to save yourself

## 📊 Game Modes

### Difficulty Levels

| Difficulty | Fuse Time | Bot Speed | Throw Speed | Notes |
|------------|-----------|-----------|-------------|-------|
| **EASY** | 9 seconds | Slow | Slow | Great for beginners |
| **MEDIUM** | 7 seconds | Moderate | Moderate | Balanced challenge |
| **HARD** | 5 seconds | Aggressive | Fast | For experienced players |

### Number of Opponents
- Adjust from **1 to 11 opponents** on the start screen
- More opponents = shorter survival times, higher scores

## 🎯 Objective

1. **Survive** — Stay alive as long as possible
2. **Pass the Ball** — When you hold the fireball, quickly pass it to avoid elimination
3. **Avoid Walls** — Don't get trapped in corners or blocked by obstacles
4. **Be the Last One Standing** — Eliminate all opponents to win

## ⏱️ Score System

Your score increases based on:
- **Survival time** — The longer you survive, the higher your score
- **Number of players** — More opponents means higher potential score
- Formula: `(Time in seconds) × (Number of players)`

## 🔥 What Happens When...

| Event | Result |
|-------|--------|
| Ball in your hand counts down to 0 | You're eliminated (ball explodes) |
| You throw to someone near a wall | Ball ricochets, passed to random player |
| You don't have the ball | Be alert — you might get it next! |
| Timer counts down (3, 2, 1) | Warning sounds increase urgency |
| You win | Last survivor gets victory screen |

## 💡 Tips & Strategies

✅ **DO:**
- React quickly when you get the ball
- Pass to nearby players to save time
- Move away from walls to avoid being cornered
- Keep an eye on the timer countdown

❌ **DON'T:**
- Hold the ball too long
- Get trapped in corners
- Cluster with other players (creates risky situations)
- Panic — stay calm and pass!

## 🚀 How to Run

1. Make sure you have **Python 3.7+** installed
2. Install dependencies:
   ```bash
   pip install pygame numpy
   ```
3. Run the game:
   ```bash
   python main.py
   ```

## 🎮 Game Flow

1. **Start Screen** — Select difficulty and number of opponents
2. **Game Start** — A random bot gets the fireball first
3. **Gameplay** — Pass the ball, avoid elimination, survive
4. **Game Over** — See the results and choose to restart or quit

## 🏆 Game Over Conditions

- **VICTORY!** — You're the last player standing
- **ELIMINATED!** — A specific bot survived (you were eliminated)
- **DRAW!** — All players eliminated at the same time

## 🎨 Features

- Smooth gameplay at 60 FPS
- Dynamic difficulty scaling
- Smart AI opponents that strategically pass the ball
- Real-time score tracking
- Screen shake effects on elimination
- Audio feedback (throw, explosion, warnings)

## 🐛 Known Issues & Solutions

If you experience issues:
- **Game stuttering** — Reduce number of opponents
- **Can't throw ball** — Make sure you have the ball and it's not flying
- **Stuck in corner** — Press keys to move away quickly

---

**Good luck, and may the last survivor be you!** 🎉

Made with ❤️ using Pygame

