use recipes_app

db.users.drop()
db.recipes.drop()
db.saves.drop()
db.comments.drop()


// Kreiraj 3 korisnika
const anaId = db.users.insertOne({
  username: "ana",
  password: "123",
  display_name: "Ana Horvat",
  bio: "Brzi ručkovi i mediteranska kuhinja.",
  created_at: new Date()
}).insertedId

const ivanId = db.users.insertOne({
  username: "ivan",
  password: "123",
  display_name: "Ivan Novak",
  bio: "Fitness + meal-prep recepti.",
  created_at: new Date()
}).insertedId

const majaId = db.users.insertOne({
  username: "maja",
  password: "123",
  display_name: "Maja Kovač",
  bio: "Volim slastice i vegetarijanska jela.",
  created_at: new Date()
}).insertedId

//  Kreiraj 6 recepata 
db.recipes.insertMany([
  {
    author_id: anaId,
    title: "Piletina s rižom",
    description: "Brzo i fino.",
    ingredients: [
      { name: "Piletina", key: "piletina", qty: 300, unit: "g" },
      { name: "Riža",     key: "riza",     qty: 200, unit: "g" },
      { name: "Luk",      key: "luk",      qty: 1,   unit: "kom" }
    ],
    ingredient_keys: ["piletina","riza","luk"],
    steps: ["Skuhaj rižu", "Ispeci piletinu", "Dodaj luk"],
    allergens: [],
    created_at: new Date()
  },
  {
    author_id: anaId,
    title: "Tjestenina s rajčicom",
    description: "Klasika za 15 minuta.",
    ingredients: [
      { name: "Tjestenina", key: "tjestenina", qty: 250, unit: "g" },
      { name: "Rajčica",    key: "rajcica",    qty: 3,   unit: "kom" },
      { name: "Češnjak",    key: "cesnjak",    qty: 2,   unit: "cesanj" }
    ],
    ingredient_keys: ["tjestenina","rajcica","cesnjak"],
    steps: ["Skuhaj tjesteninu", "Skuhaj umak", "Pomiješaj i posluži"],
    allergens: ["gluten"],
    created_at: new Date()
  },

  {
    author_id: ivanId,
    title: "Zobena kaša s bananom",
    description: "Doručak bez komplikacija.",
    ingredients: [
      { name: "Zobene pahuljice", key: "zob",     qty: 60,  unit: "g" },
      { name: "Mlijeko",          key: "mlijeko", qty: 250, unit: "ml" },
      { name: "Banana",           key: "banana",  qty: 1,   unit: "kom" }
    ],
    ingredient_keys: ["zob","mlijeko","banana"],
    steps: ["Skuhaj zob u mlijeku", "Dodaj narezanu bananu"],
    allergens: ["gluten","mlijeko"],
    created_at: new Date()
  },
  {
    author_id: ivanId,
    title: "Proteinski omlet",
    description: "Brz obrok s puno proteina.",
    ingredients: [
      { name: "Jaja",    key: "jaja",    qty: 3,   unit: "kom" },
      { name: "Šunka",   key: "sunka",   qty: 80,  unit: "g" },
      { name: "Sir",     key: "sir",     qty: 50,  unit: "g" }
    ],
    ingredient_keys: ["jaja","sunka","sir"],
    steps: ["Umuti jaja", "Dodaj šunku i sir", "Ispeci na tavi"],
    allergens: ["jaja","mlijeko"],
    created_at: new Date()
  },

  {
    author_id: majaId,
    title: "Salata od slanutka",
    description: "Vegetarijanska i zasitna.",
    ingredients: [
      { name: "Slanutak", key: "slanutak", qty: 240, unit: "g" },
      { name: "Rajčica",  key: "rajcica",  qty: 2,   unit: "kom" },
      { name: "Luk",      key: "luk",      qty: 1,   unit: "kom" }
    ],
    ingredient_keys: ["slanutak","rajcica","luk"],
    steps: ["Isperi slanutak", "Nareži povrće", "Sve pomiješaj i začini"],
    allergens: [],
    created_at: new Date()
  },
  {
    author_id: majaId,
    title: "Palačinke s orasima",
    description: "Slastica za vikend.",
    ingredients: [
      { name: "Brašno",  key: "brasno",  qty: 200, unit: "g" },
      { name: "Mlijeko", key: "mlijeko", qty: 300, unit: "ml" },
      { name: "Jaja",    key: "jaja",    qty: 2,   unit: "kom" },
      { name: "Orah",    key: "orah",    qty: 80,  unit: "g" }
    ],
    ingredient_keys: ["brasno","mlijeko","jaja","orah"],
    steps: ["Umuti smjesu", "Ispeci palačinke", "Nadjev: mljeveni orah"],
    allergens: ["gluten","mlijeko","jaja","orasasti_plodovi"],
    created_at: new Date()
  }
])

db.users.createIndex({ username: 1 }, { unique: true })
db.recipes.createIndex({ author_id: 1 })
db.recipes.createIndex({ created_at: -1 })
db.recipes.createIndex({ ingredient_keys: 1 })
db.recipes.createIndex({ allergens: 1 })
