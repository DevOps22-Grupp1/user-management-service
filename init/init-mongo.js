db.createUser({
    user: "sudo_admin",
    pwd: "password",
    roles: [
        {
            role: "readWrite",

            db: "allUsers",


        },
    ],
});

db.createCollection("users");
db.users.insertMany([
    {
        id: 1,
        name: "Max Svensson",
        email: "me@gmail.com",
        avatar: "https://robohash.org/ametveldolorem.png?size=50x50&set=set1",
        username: "emclinden0",
        password: "lC2)Pug$Dsq*8b|6",
        role: "admin",
        bought: []
    },
    {
        id: 2,
        name: "Jarl Svensson",
        email: "js@gmail.com",
        avatar: "https://robohash.org/quidemvelitut.png?size=50x50&set=set1",
        username: "tjewar1",
        password: "tO6(.zfUWLjNVF",
        role: "admin",
        bought: []
    },
    {
        id: 3,
        name: "Harisha Svensson",
        email: "hs@gmail.com",
        avatar: "https://robohash.org/asperioresipsamitaque.png?size=50x50&set=set1",
        username: "sgwyneth5",
        password: "jT7`pjwWNiT.C",
        role: "customer",
        bought: []
    },
    {
        id: 4,
        name: "Dennis Svensson",
        email: "ds@gmail.com",
        avatar: "https://robohash.org/harumdelectusratione.png?size=50x50&set=set1",
        username: "akamen2",
        password: "dP7(kp,/uW?'(j",
        role: "admin",
        bought: []
    },
    {
        id: 5,
        name: "Simon Svensson",
        email: "ss@gmail.com",
        avatar: "https://robohash.org/commodisimiliquesunt.png?size=50x50&set=set1",
        username: "cmor3",
        password: "uK6+bn46xMPfO#j",
        role: "customer",
        bought: []
    },
    {
        id: 6,
        name: "Zoreh Svensson",
        email: "zs@gmail.com",
        avatar: "https://robohash.org/vitaeporroid.png?size=50x50&set=set1",
        username: "rporker4",
        password: "yR7mZ*4eBKXl",
        role: "customer",
        bought: []
    },

    {
        id: 7,
        name: "Testy de Admin",
        email: "user2@test.se",
        avatar: "https://robohash.org/laboriosamofficiisnihil.png?size=50x50&set=set1",
        username: "admin",
        password: "admin",
        role: "admin",
        bought: []
    },
    {
        id: 8,
        name: "Testy de Testsson",
        email: "user1@test.se",
        avatar: "https://robohash.org/delenitiducimusea.png?size=50x50&set=set1",
        username: "user1",
        password: "password1",
        role: "customer",
        bought: []
    },

]);

