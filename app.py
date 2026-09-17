function injecterResultatsDepuisVisuel() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var feuilleSource = ss.getActiveSheet(); 
  var feuilleParticipations = ss.getSheetByName("PARTICIPATIONS");
  
  if (!feuilleParticipations) {
    SpreadsheetApp.getUi().alert("❌ Onglet 'PARTICIPATIONS' introuvable.");
    return;
  }
  if (feuilleSource.getName() === "PARTICIPATIONS") {
    SpreadsheetApp.getUi().alert("❌ Place-toi sur l'onglet de tes résultats (ex: RESULTATS_EXTRAITS) avant de lancer.");
    return;
  }

  var diminutifs = {
    "FRED": "FREDERIC",
    "LUDO": "LUDOVIC",
    "SEB": "SEBASTIEN",
    "STEPH": "STEPHANE",
    "GREG": "GREGORY",
    "CHRIS": "CHRISTOPHE",
    "MATH": "MATHIEU",
    "JEFF": "JEAN FRANCOIS"
  };

  function normaliser(texte) {
    if (!texte) return "";
    return texte.toString()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toUpperCase();
  }

  function correspondreNoms(nomSaisi, nomInscrit) {
    if (!nomSaisi || !nomInscrit) return false;
    
    var motsSaisis = nomSaisi.split(" ");
    var motsInscrits = nomInscrit.split(" ");
    
    for (var i = 0; i < motsSaisis.length; i++) {
      var motS = motsSaisis[i];
      if (!motS || motS.length < 2) continue;
      
      var motSEtendu = diminutifs[motS] || motS;
      var trouve = false;
      
      for (var j = 0; j < motsInscrits.length; j++) {
        var motI = motsInscrits[j];
        if (motI.indexOf(motS) === 0 || motI.indexOf(motSEtendu) === 0 || motSEtendu.indexOf(motI) === 0) {
          trouve = true;
          break;
        }
      }
      if (!trouve) return false;
    }
    return true;
  }

  // 1. Repérage des colonnes dans PARTICIPATIONS (D=3, E=4, G=6, H=7)
  var partData = feuilleParticipations.getDataRange().getValues();
  var headers = partData[0];
  
  var idxMembre = 3;   // Col D
  var idxCourse = 4;   // Col E
  var idxStatut = 6;   // Col G
  var idxResultat = 7; // Col H

  for (var col = 0; col < headers.length; col++) {
    var hNorm = normaliser(headers[col]);
    if (hNorm.indexOf("MEMBRE") !== -1) idxMembre = col;
    if (hNorm.indexOf("COURSE") !== -1) idxCourse = col;
    if (hNorm.indexOf("STATUT") !== -1) idxStatut = col;
    if (hNorm.indexOf("RESULTAT") !== -1 || hNorm.indexOf("SULTAT") !== -1) idxResultat = col;
  }

  var inscritsParCourse = {};
  for (var i = 1; i < partData.length; i++) {
    var cNorm = normaliser(partData[i][idxCourse]);
    var mNorm = normaliser(partData[i][idxMembre]);
    if (cNorm && mNorm) {
      if (!inscritsParCourse[cNorm]) inscritsParCourse[cNorm] = [];
      inscritsParCourse[cNorm].push({ rowIdx: i, nomComplet: mNorm });
    }
  }

  // 2. Parcourir l'onglet source
  var sourceData = feuilleSource.getDataRange().getValues();
  var currentCourseNorm = "";
  var compteMisesAJour = 0;

  for (var r = 0; r < sourceData.length; r++) {
    var valC = sourceData[r][2] ? sourceData[r][2].toString().trim() : (sourceData[r][0] ? sourceData[r][0].toString().trim() : "");
    var valD = sourceData[r][3] ? sourceData[r][3].toString().trim() : (sourceData[r][1] ? sourceData[r][1].toString().trim() : "");

    if (!valC && !valD) continue;

    // Titre de course
    if (valC && !valD && !valC.includes("/")) {
      currentCourseNorm = normaliser(valC);
      continue;
    }

    // Résultat + Membre
    if (currentCourseNorm && valC && valD) {
      var resultat = valC;
      var listeNomsSaisis = valD.split(/\bet\b|,|&|\||\+/i);

      var courseClefFound = null;
      if (inscritsParCourse[currentCourseNorm]) {
        courseClefFound = currentCourseNorm;
      } else {
        for (var cKey in inscritsParCourse) {
          if (cKey.includes(currentCourseNorm) || currentCourseNorm.includes(cKey)) {
            courseClefFound = cKey;
            break;
          }
        }
      }

      if (courseClefFound) {
        var listeInscrits = inscritsParCourse[courseClefFound];
        
        for (var n = 0; n < listeNomsSaisis.length; n++) {
          var nomSaisiNorm = normaliser(listeNomsSaisis[n]);
          if (!nomSaisiNorm) continue;

          for (var k = 0; k < listeInscrits.length; k++) {
            if (correspondreNoms(nomSaisiNorm, listeInscrits[k].nomComplet)) {
              var ligneCible = listeInscrits[k].rowIdx;
              partData[ligneCible][idxResultat] = resultat;
              partData[ligneCible][idxStatut] = "Finisher"; // Valeur exacte autorisée
              compteMisesAJour++;
            }
          }
        }
      }
    }
  }

  // 3. Sauvegarde
  feuilleParticipations.getDataRange().setValues(partData);
  SpreadsheetApp.getUi().alert("✅ " + compteMisesAJour + " classements associés et statuts passés en 'Finisher' !");
}