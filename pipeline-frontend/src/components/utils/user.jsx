// utils/user.js

export function getUserId() {
    let uid = localStorage.getItem("uid");

    if (!uid) {
        uid = crypto.randomUUID();
        localStorage.setItem("uid", uid);
    }

    return uid;
}