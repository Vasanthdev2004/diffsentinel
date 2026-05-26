def find_matching_users(users, active_ids):
    matches = []
    for user in users:
        for active_id in active_ids:
            if user["id"] == active_id:
                matches.append(user)
    return matches
