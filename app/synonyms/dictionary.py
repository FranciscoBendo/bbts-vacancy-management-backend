"""
Dicionário fixo de sinônimos de skills.
Para adicionar: edite o dict SYNONYMS abaixo.
Formato: "variação" -> "termo canônico"
"""
SYNONYMS: dict[str, str] = {
    "js": "javascript", "javascript": "javascript", "ecmascript": "javascript",
    "es6": "javascript", "node": "node.js", "nodejs": "node.js", "node.js": "node.js",
    "next": "next.js", "nextjs": "next.js", "next.js": "next.js",
    "react.js": "react", "reactjs": "react",
    "vue.js": "vue", "vuejs": "vue",
    "angular.js": "angular", "angularjs": "angular",
    "python3": "python", "python 3": "python", "py": "python",
    "drf": "django", "django rest framework": "django",
    "java 17": "java", "java 11": "java", "java 8": "java",
    "spring": "spring boot", "springboot": "spring boot", "spring framework": "spring boot",
    "aws": "aws", "amazon web services": "aws",
    "gcp": "google cloud", "google cloud platform": "google cloud",
    "azure": "microsoft azure",
    "spark": "apache spark", "pyspark": "apache spark",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "elastic": "elasticsearch",
    "k8s": "kubernetes", "kube": "kubernetes",
    "ml": "machine learning", "dl": "deep learning",
    "english": "inglês", "inglês": "inglês", "ingles": "inglês",
    "espanhol": "espanhol", "spanish": "espanhol",
    "rn": "react native",
    "ci/cd": "ci/cd", "cicd": "ci/cd",
}

def normalize_skill(skill: str) -> str:
    key = skill.lower().strip()
    return SYNONYMS.get(key, key)

def normalize_skills(skills: list[str]) -> list[str]:
    seen, result = set(), []
    for s in skills:
        n = normalize_skill(s)
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result
