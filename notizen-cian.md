

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



zweite function ist dafür da um 

