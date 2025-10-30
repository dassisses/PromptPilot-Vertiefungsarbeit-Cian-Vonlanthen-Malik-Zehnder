

Planung änderungen refactor backend: 

Was soll das backend alles für schnitstellen bieten für das frontend? 


verwaltung von preset json

hirbie soll zuerst gecheckt werden ob preset json vorhanden ist wenn nicht wird ein default preset json erstellt

function zur werwaltung von preset json : 

diese funktion soll folgendes machen: 

wenn von einer anderen funktion angesteurt dann muss folgendes der funktion mitgegben post update oder delete 

bei post wird ein neues preset im json erstellt das wäre dann der zweite paramter der promt und dann noch denn api typ 

[{"name": "Translation to Spanish", "prompt": "Uebersetze mir folgenden text auf spanisch: ", "api_type": "chatgpt"}]


bei delete wird der name des presets mitgegeben und dieser wird dann aus dem preset json gelöscht

bei update wird der name des presets mitgegeben und der neue prompt und api typ und dieser wird dann im preset json geupdated

Antowort ist immer succes oder fail mit einer spezifischen message zum jeweilgien case. 



zweite function ist dafür da um um die credentials zu managen


diese function soll folgendes machen:

erstens check ob das credential json vorhanden ist wenn nicht wird ein leeres credential json erstellt

function zur verwaltung von credential json :

hierbei ist die gleiche lokig wie bei der preset json

bei post wird ein neues credential im json erstellt das wäre dann der zweite paramter der promt und dann noch denn api typ 

[{"name": "OpenAI", "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}]

bei delete wird der name des credentials mitgegeben und dieser wird dann aus dem credential json gelöscht

bei update wird der name des credentials mitgegeben und der neue api key und dieser wird dann im credential json geupdated


Antowrt ist immer succes oder fail mit einer spezifischen message zum jeweilgien case.

function zur ausführung eines presets: 

diese function soll folgendes machen:

die function bekommt folgende paramter mitgegeben: preset name, input von user 

function sucht dann das preset im preset json raus und den api typ anahnd des eingetragen typs im preset json 

anschliessend wird ein Api abruf auf die jeweilige schnittstelle gemacht mit dem prompt aus dem preset json und dem input vom user

antwort wird dann an das frontend zurückgegeben

antwort ist immer der output von der jeweiligen schnittstelle oder fail mit einer spezifischen message zum jeweilgien case.

dritte function zur ausführung eines credentials test:

diese function soll folgendes machen:

die function bekommt folgende paramter mitgegeben: credential name

function sucht dann das credential im credential json raus und den api key anahnd des eingetragen typs im credential json




