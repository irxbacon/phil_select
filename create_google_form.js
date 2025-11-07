/**
 * Google Apps Script function to create a Google Form that mimics the Phil Select Survey
 * 
 * To use this:
 * 1. Go to https://script.google.com
 * 2. Create a new project
 * 3. Replace the default code with this function
 * 4. Run the createPhilSelectSurvey() function
 * 5. Check the logs for the form URL
 * 
 * This creates a form that matches the structure of templates/survey.html
 */
function createPhilSelectSurvey() {
  // Create a new form
  var form = FormApp.create('Phil Select - Crew Member Program Survey');
  
  // Set form description
  form.setDescription('Please fill out this survey to help us understand your interests and experience levels with various Philmont programs.');
  
  // ===== SECTION 1: Personal Information =====
  var personalSection = form.addSectionHeaderItem();
  personalSection.setTitle('Personal Information');
  
  // Full Name
  var nameItem = form.addTextItem();
  nameItem.setTitle('Full Name')
    .setRequired(true);
  
  // Age
  var ageItem = form.addTextItem();
  ageItem.setTitle('Age')
    .setValidation(FormApp.createTextValidation()
      .requireWholeNumber()
      .setHelpText('Please enter a number between 1 and 100')
      .build());
  
  // Overall Outdoor Experience
  var skillLevelItem = form.addScaleItem();
  skillLevelItem.setTitle('Overall Outdoor Experience')
    .setBounds(1, 5)
    .setLabels('Beginner', 'Expert')
    .setRequired(true);
  
  // ===== SECTION 2: Program Interest & Experience Rating =====
  var programSection = form.addSectionHeaderItem();
  programSection.setTitle('Program Interest');
  programSection.setHelpText('Rate each program from 0-20 based on your interest and experience level (1 = No Interest, 20 = Very High Interest)');
  
  // Define all programs organized by category (from database query)
  var programsByCategory = {
    'COPE': [
      {id: 5, name: 'COPE: High Challenge Course', code: 'COPE__High_Challenge'},
      {id: 6, name: 'COPE: Initiative Games', code: 'COPE__Initiative_Gam'},
      {id: 7, name: 'COPE: Low Challenge Course', code: 'COPE__Low_Challenge_'}
    ],
    'Climbing': [
      {id: 1, name: 'Climbing: Bouldering Gym', code: 'Climbing__Bouldering'},
      {id: 2, name: 'Climbing: Climbing Wall/Tower', code: 'Climbing__Climbing_W'},
      {id: 3, name: 'Climbing: Crate Stacking', code: 'Climbing__Crate_Stac'},
      {id: 4, name: 'Climbing: Rock Climbing', code: 'Climbing__Rock_Climb'}
    ],
    'Ecology': [
      {id: 8, name: 'Ecology: Demonstration Forest', code: 'Ecology__Demonstrati'},
      {id: 9, name: 'Ecology: Self-Guided Fishing', code: 'Ecology__Self_Guided'}
    ],
    'Evening': [
      {id: 10, name: 'Evening: Abreu Family Dinner', code: 'Evening__Abreu_Famil'},
      {id: 11, name: 'Evening: Advisor Coffee', code: 'Evening__Advisor_Cof'},
      {id: 12, name: 'Evening: Campfire Show', code: 'Evening__Campfire_Sh'},
      {id: 13, name: 'Evening: Chuckwagon Dinner', code: 'Evening__Chuckwagon_'}
    ],
    'General': [
      {id: 38, name: 'Low Impact Camping', code: 'Low_Impact_Camping'}
    ],
    'Historical': [
      {id: 14, name: 'Historical: Adobe Brick-Making', code: 'Historical__Adobe_Br'},
      {id: 15, name: 'Historical: Blacksmithing', code: 'Historical__Blacksmi'},
      {id: 16, name: 'Historical: Cabin Restoration', code: 'Historical__Cabin_Re'},
      {id: 17, name: 'Historical: Cabin/House Tour', code: 'Historical__Cabin_Ho'},
      {id: 18, name: 'Historical: Crafting', code: 'Historical__Crafting'},
      {id: 19, name: 'Historical: Crosscut & Tie Making', code: 'Historical__Crosscut'},
      {id: 20, name: 'Historical: Flint Knapping', code: 'Historical__Flint_Kn'},
      {id: 21, name: 'Historical: Fur Trapper Rendezvous', code: 'Historical__Fur_Trap'},
      {id: 22, name: 'Historical: Gold Panning', code: 'Historical__Gold_Pan'},
      {id: 23, name: 'Historical: Mine Tour', code: 'Historical__Mine_Tou'},
      {id: 24, name: 'Historical: Petroglyph Tour', code: 'Historical__Petrogly'},
      {id: 25, name: 'Historical: Pump Car Rides', code: 'Historical__Pump_Car'},
      {id: 26, name: 'Historical: Railroad Construction', code: 'Historical__Railroad'},
      {id: 27, name: 'Historical: Spar Pole Climbing', code: 'Historical__Spar_Pol'}
    ],
    'Landmarks': [
      {id: 28, name: 'Landmarks: Baldy Mountain', code: 'Landmarks__Baldy_Mou'},
      {id: 29, name: 'Landmarks: Inspiration Point', code: 'Landmarks__Inspirati'},
      {id: 30, name: 'Landmarks: Mount Phillips', code: 'Landmarks__Mount_Phi'},
      {id: 31, name: 'Landmarks: Mountaineering', code: 'Landmarks__Mountaine'},
      {id: 32, name: 'Landmarks: Tooth of Time', code: 'Landmarks__Tooth_of_'},
      {id: 33, name: 'Landmarks: Trail Peak', code: 'Landmarks__Trail_Pea'}
    ],
    'Livestock': [
      {id: 34, name: 'Livestock: Animal Husbandry', code: 'Livestock__Animal_Hu'},
      {id: 35, name: 'Livestock: Burro Packing', code: 'Livestock__Burro_Pac'},
      {id: 36, name: 'Livestock: Chicken Tending', code: 'Livestock__Chicken_T'},
      {id: 37, name: 'Livestock: Horse Rides', code: 'Livestock__Horse_Rid'}
    ],
    'Range Sports': [
      {id: 39, name: 'Range Sports: 3D Archery', code: 'Range_Sports__3D_Arc'},
      {id: 40, name: 'Range Sports: Aerial Archery', code: 'Range_Sports__Aerial'},
      {id: 41, name: 'Range Sports: Atlatl Throwing', code: 'Range_Sports__Atlatl'},
      {id: 42, name: 'Range Sports: Cartridge Reloading', code: 'Range_Sports__Cartri'},
      {id: 43, name: 'Range Sports: Cowboy Action Shooting', code: 'Range_Sports__Cowboy'},
      {id: 44, name: 'Range Sports: Field Archery', code: 'Range_Sports__Field_'},
      {id: 45, name: 'Range Sports: Muzzleloader Shooting', code: 'Range_Sports__Muzzle'},
      {id: 46, name: 'Range Sports: Rifle Shooting', code: 'Range_Sports__Rifle_'},
      {id: 47, name: 'Range Sports: Shotgun Shooting', code: 'Range_Sports__Shotgu'},
      {id: 48, name: 'Range Sports: Shotshell Reloading', code: 'Range_Sports__Shotsh'},
      {id: 49, name: 'Range Sports: Tomahawk Throwing', code: 'Range_Sports__Tomaha'}
    ],
    'STEM': [
      {id: 50, name: 'STEM: Archeology', code: 'STEM__Archeology'},
      {id: 51, name: 'STEM: Astronomy', code: 'STEM__Astronomy'},
      {id: 52, name: 'STEM: Geology', code: 'STEM__Geology'}
    ],
    'Western Lore': [
      {id: 53, name: 'Western Lore: Branding', code: 'Western_Lore__Brandi'},
      {id: 54, name: 'Western Lore: Cantina', code: 'Western_Lore__Cantin'},
      {id: 55, name: 'Western Lore: Roping', code: 'Western_Lore__Roping'}
    ],
    'Wheeled': [
      {id: 56, name: 'Wheeled: Mountain Biking', code: 'Wheeled__Mountain_Bi'}
    ]
  };
  
  // Add program rating questions organized by category
  var categories = Object.keys(programsByCategory);
  for (var i = 0; i < categories.length; i++) {
    var category = categories[i];
    var programs = programsByCategory[category];

    // Add each program in this category
    for (var j = 0; j < programs.length; j++) {
      var program = programs[j];
      var programItem = form.addListItem();
      
      // Create dropdown choices from 0-20 with default value of 10
      var choices = [];
      for (var k = 0; k <= 20; k++) {
        if (k === 10) {
          choices.push(programItem.createChoice(k.toString(), true)); // true makes this the default
        } else {
          choices.push(programItem.createChoice(k.toString()));
        }
      }
      
      programItem.setTitle(program.name)
        .setChoices(choices)
        .setHelpText('Rate from 0 (No Interest) to 20 (Very High Interest)')
        .setRequired(true);
    }
  }
  
  // Set form settings
  form.setCollectEmail(true);
  form.setLimitOneResponsePerUser(false);
  form.setShowLinkToRespondAgain(true);
  
  // Set confirmation message
  form.setConfirmationMessage('Thank you for completing the Phil Select survey! Your responses have been recorded.');
  
  // Get the form URL and log it
  var formUrl = form.getPublishedUrl();
  Logger.log('Phil Select Survey Form created successfully!');
  Logger.log('Form URL: ' + formUrl);
  Logger.log('Form ID: ' + form.getId());
  
  // Return the form URL for use in other functions
  return {
    url: formUrl,
    id: form.getId(),
    editUrl: form.getEditUrl()
  };
}

/**
 * Helper function to get the created form's responses as a spreadsheet
 */
function linkFormToSpreadsheet(formId) {
  var form = FormApp.openById(formId);
  var spreadsheet = SpreadsheetApp.create('Phil Select Survey Responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, spreadsheet.getId());
  
  Logger.log('Responses will be collected in: ' + spreadsheet.getUrl());
  return spreadsheet.getUrl();
}

/**
 * Example usage function - demonstrates how to create the form and set up response collection
 */
function setupCompletePhilSelectSurvey() {
  // Create the form
  var formInfo = createPhilSelectSurvey();
  
  // Link it to a spreadsheet for response collection
  var spreadsheetUrl = linkFormToSpreadsheet(formInfo.id);
  
  Logger.log('=== Phil Select Survey Setup Complete ===');
  Logger.log('Survey Form URL: ' + formInfo.url);
  Logger.log('Form Edit URL: ' + formInfo.editUrl);
  Logger.log('Responses Spreadsheet: ' + spreadsheetUrl);
  Logger.log('======================================');
  
  return {
    form: formInfo,
    spreadsheet: spreadsheetUrl
  };
}