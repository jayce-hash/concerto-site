def spread(points, gap=0.022, rounds=40):
    for _ in range(rounds):
        moved = False
        for i, a in enumerate(points):
            for b in points[i + 1:]:
                if a['level'] != b['level']: continue
                dx, dy = b['x'] - a['x'], b['y'] - a['y']; d = math.hypot(dx, dy)
                if d < gap:
                    push = (gap - d) / 2
                    ux, uy = (dx / d, dy / d) if d else (1.0, 0.0)  # same spot: split them sideways
                    a['x'] -= ux * push; a['y'] -= uy * push
                    b['x'] += ux * push; b['y'] += uy * push
                    moved = True
        if not moved: break
    for q in points: q['x'], q['y'] = round(min(max(q['x'], 0.01), 0.99), 4), round(min(max(q['y'], 0.01), 0.99), 4)
spread(points)

