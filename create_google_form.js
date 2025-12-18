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
  
// Define all programs organized by category (from database - updated 2025-12-17)
  var programsByCategory = {
    'COPE': [
      {name: 'COPE: High Challenge Course', code: 'COPE__High_Challenge', description: 'The High Ropes Course & Climbing Tower is where your crew will participate in an exciting series of team building and climbing events on Philmont\'s COPE (Challenging Outdoor Personal Experience) tower. Highly trained staff of the Philmont Training Center staff will lead you in these activities.'},
      {name: 'COPE: Initiative Games', code: 'COPE__Initiative_Gam', description: 'Low COPE games to test yourself and your crew. These will help your crew work together to meet the challenges of your trek.'},
      {name: 'COPE: Low Challenge Course', code: 'COPE__Low_Challenge_', description: 'A series of “ropes” activities that will test the teamwork, skill, and resourcefulness of your crew awaits you at Dan Beard, Head of Dean, and Urraca camps. While the challenges can be met by every crew, the real contest is with yourself. Did you do your best? How would you do better next time? What did your crew learn that will help you work together to meet the challenges of your trek?'}
    ],
    'Climbing': [
      {name: 'Climbing: Bouldering Gym', code: 'Climbing__Bouldering', description: 'While not as technical as Rock Climbing, bouldering gives you the opportunity to practice climbing without equipment at Philmont’s indoor climbing gyms — using just your hands and feet!'},
      {name: 'Climbing: Climbing Wall/Tower', code: 'Climbing__Climbing_W', description: 'While not as technical as Rock Climbing, this program gives you the opportunity to practice climbing at Philmont’s outdoor climbing walls.'},
      {name: 'Climbing: Crate Stacking', code: 'Climbing__Crate_Stac', description: 'A fun climbing activity, crews compete to see how high they can stack crates!'},
      {name: 'Climbing: Rock Climbing', code: 'Climbing__Rock_Climb', description: 'This fascinating and challenging sport is a favorite of all Philmont campers. You will scale a steep pitch and rappel down a sheer cliff. Philmont has carefully selected areas to conduct this program where the rocks are safe and practical, but a distinct “Class Five” challenge. Under the supervision of expert climbers, you will climb using your hands and feet while protected by rope, carabineers, and helmet. Safety is always stressed and practiced.'}
    ],
    'Ecology': [
      {name: 'Ecology: Fire Ecology Program', code: 'Ecology__Fire_Ecolog', description: 'Between Hunting Lodge and Clarks Fork, near Cito Reservoir, a Demonstration Forest has been developed with the support of the American Tree Farm Organization. Your crew will spend time with professional foresters to learn about the forests and various forest practices taking place at Philmont.'},
      {name: 'Ecology: Forestry', code: 'Ecology__Forestry', description: 'Between Hunting Lodge and Clarks Fork, near Cito Reservoir, a Demonstration Forest has been developed with the support of the American Tree Farm Organization. Your crew will spend time with professional foresters to learn about the forests and various forest practices taking place at Philmont.'},
      {name: 'Ecology: Self-Guided Fishing', code: 'Ecology__Self_Guided', description: 'The Rayado and Agua Fria streams in the south offer excellent trout fishing. Additionally, the Cito Reservoir near the Hunting Lodge provides great lake fishing. Though not large, these trout are wary and exciting to catch. Fly rods may be checked out at the Hunting Lodge, Fish Camp, Abreu, and Phillips Junction or you may bring your own.'}
    ],
    'Evening': [
      {name: 'Evening: Abreu Family Dinner', code: 'Evening__Abreu_Famil', description: 'In keeping with the southwestern spirit of the program at Abreu, you will be instructed in helping to prepare a special Mexican meal.'},
      {name: 'Evening: Advisor Coffee', code: 'Evening__Advisor_Cof', description: 'In staff camps, Advisors meet at the main cabin for coffee and snacks in the evening after dinner. This gives the Advisors a chance to compare their experiences while the youth crewmembers can socialize with other crews in the campsite.'},
      {name: 'Evening: Campfire Show', code: 'Evening__Campfire_Sh', description: 'Throughout the backcountry, various staffed camps conduct special evening campfires and programs. Urraca Mesa’s campfire will regale your crew with some of the most famous ghost stories and mysterious lore of the ranch with music and songs to boot! Pueblano, and Crater Lake campfires relate to the tales of the Old West, logging, and the history of the land. Facts about the Beaubien-Miranda Land Grant come alive, and the influence of Waite Phillips and his gift of Philmont to the BSA provides for a special inspiration. At Beaubien and Clarks Fork, the focus is on the Old West with its songs and stories and true cowboy atmosphere. Ponil offers a nightly Old West Cantina show. At Cyphers Mine, the story of gold will ring through your ears as an interpreter relates the life and adventures of the miners of yesteryear at the nightly “STOMP”. At Metcalf Station, be ready for the Railroad Jubilee Campfire that regales stories and songs of railroading history and lore. At Rich Cabins enjoy the family gathering and hear some stories and music regaling the life of the Rich family.'},
      {name: 'Evening: Chuckwagon Dinner', code: 'Evening__Chuckwagon_', description: 'The programs at Clark’s Fork, Beaubien, and Ponil include a special chuck wagon dinner for many crews that pass through. Members of your crew will help prepare these meals.'}
    ],
    'General': [
      {name: 'Low Impact Camping', code: 'Low_Impact_Camping', description: 'Wildland ethic depends upon attitude and awareness rather than on rules and regulations. While camping off Philmont property in the Valle Vidal or any other locations, you are expected to employ Leave No Trace methods taught at Dan Beard, Rich Cabins, and other points where you leave Philmont property. You will have the opportunity to learn how to enjoy wildland with respect to hiking, camping, eating meals, and disposal of trash without leaving a scar or trace. You will also receive further “Leave No Trace” information at Whiteman Vega and Ring Place. Your Wilderness Pledge Guia and Ranger will help you learn the techniques of Leave No Trace.'}
    ],
    'Hazard': [
      {name: 'Hazard: Fire Recovery Zone', code: 'Hazard__Fire_Recover', description: ''}
    ],
    'Historical': [
      {name: 'Historical: Adobe Brick-Making', code: 'Historical__Adobe_Br', description: 'You will become acquainted with the techniques used in the construction of southwestern architecture. After mixing a batch of adobe mud, using a special formula of clay, straw, water, and sand, you pack it into wooden forms to mold bricks. When the bricks have dried from the solar energy of the New Mexico sun, they are used for construction.'},
      {name: 'Historical: Archaeological Dig Site', code: 'Historical__Archaeol', description: ''},
      {name: 'Historical: Assaying', code: 'Historical__Assaying', description: ''},
      {name: 'Historical: Blacksmithing', code: 'Historical__Blacksmi', description: 'The ring of hammer striking iron echoes through the mountains around French Henry, Black Mountain, Cypher’s Mine, and Metcalf Station camps. Here, staff blacksmiths will acquaint you with a working forge, blower, leg vice, hardie, and an array of tongs used to grip red-hot iron. The blacksmith will discuss and demonstrate techniques for firing the forge, working metal, and tempering the finished product.'},
      {name: 'Historical: Cabin/House Tour', code: 'Historical__Cabin_Ho', description: 'Fish Camp and Hunting Lodge were two of Waite Phillip’s backcountry cabins where he entertained famous people. You will be able to experience the way they “roughed it” in the backcountry in the 1930’s. At Abreu, Crooked Creek, and Rich Cabins you will see how early homesteaders lived.'},
      {name: 'Historical: Colfax County War', code: 'Historical__Colfax_C', description: ''},
      {name: 'Historical: Crosscut & Tie Making', code: 'Historical__Crosscut', description: 'You will use two-person crosscut saws and other vintage tools to make railroad ties as the workers at the Continental Tie & Lumber Company did in the early part of the 20th century. Competition in exciting logging events such as log toss, cross-cut sawing, and log tong races will challenge your crew.'},
      {name: 'Historical: Fiber Arts', code: 'Historical__Fiber_Ar', description: ''},
      {name: 'Historical: Flint Knapping', code: 'Historical__Flint_Kn', description: 'At Apache Springs you will learn to make (knap) flint arrowheads and other tools the way the Jicarilla Apache’s did when they lived in the area.'},
      {name: 'Historical: Food/Cooking Demos', code: 'Historical__Food/Coo', description: ''},
      {name: 'Historical: Fur Trapping', code: 'Historical__Fur_Trap', description: 'Catch some of the flavor of a Fur Trapper’s rendezvous while at Miranda. Find out why rendezvous were held and what went on. See demonstrations of the mountain man way of life and participate in some of these skills and contests such as tomahawk throwing and muzzle-loading rifles.'},
      {name: 'Historical: Gold Panning', code: 'Historical__Gold_Pan', description: 'Gold is still found in almost all streams at Philmont, which was once the scene of lucrative gold-mining operations. Mine shafts, sluice boxes, and placer mines dot the mountainsides and valleys. If your itinerary takes you to Cyphers Mine or French Henry, you will tour a real gold mine. Not working now, the mines are carefully maintained so you can tour the mine shaft. Bring your jacket and a flashlight for the tour. Learn about adventures and hardships as determined miners sought their fortunes in these historic mountains. When you find some gold, ask one of the staff miners for some cellophane tape so you can take your discovery home. Gold pans are available for you to use at Cyphers Mine and French Henry. You may even run across one of our Roving Prospectors; they will help you learn about gold panning and prospecting too!'},
      {name: 'Historical: Mine Tour', code: 'Historical__Mine_Tou', description: 'Gold mining was an important part of the history of Philmont, which was once the scene of lucrative gold-mining operations. Mineshafts, sluice boxes, and placer mines dot the mountainsides and valleys. Cypher’s Mine provides you with the chance to go into a real gold mine. Not working now, the mine is carefully shored so you can tour the mine tunnels. Bring your jacket and flashlight for the tour. Learn about adventures that were experienced during the fascinating and colorful past as determined miners sought their fortunes in these historic mountains.'},
      {name: 'Historical: Mining History', code: 'Historical__Mining_H', description: ''},
      {name: 'Historical: Museum Tour', code: 'Historical__Museum_T', description: ''},
      {name: 'Historical: Petroglyph Tour', code: 'Historical__Petrogly', description: 'Near Indian Writings camp in the North Ponil Canyon take a guided tour to see the petroglyphs carved in the rocks by the ancient Puebloan settlers.'},
      {name: 'Historical: Pump Car Ride', code: 'Historical__Pump_Car', description: 'At Metcalf Station, your crew will have the opportunity to use a Pump Car to ride the rails the way railroad workers did during the early 1900’;s when the Cimarron & Northwestern Railway was in operation. It’s easier to go downhill than up!'},
      {name: 'Historical: Railroad Construction', code: 'Historical__Railroad', description: 'At Metcalf Station, learn about the history of the Cimarron & Northwestern Railway and experience what it was like to build a railroad in the early 1900’s. The ringing sounds of the mauls driving spikes, the “tick-tick” of the telegraph, combined with the smell of coal burning in the blacksmith’s forge will fill the air just like it did in 1907. Your crew will have the opportunity to lay ties and rails and spike them down as Philmont reconstructs the early logging railroad that was here.'},
      {name: 'Historical: Rayado Rancho', code: 'Historical__Rayado_R', description: ''},
      {name: 'Historical: Spar Pole Climbing', code: 'Historical__Spar_Pol', description: ''},
      {name: 'Historical: Sweat Lodge', code: 'Historical__Sweat_Lo', description: 'The exciting legend of the loggers with the Continental Tie and Lumber Company will come to life through the staff at Pueblano and Crater Lake. They will share their skills of spar pole climbing and the use of wood tools and instruments. You will use spikes on your feet and a leather strap to climb to the top of a “spar” — a tree with no limbs! See what is at the top of it!'}
    ],
    'Land Navigation': [
      {name: 'Land Navigation: Meadow Walking', code: 'Land_Navigation__Mea', description: ''}
    ],
    'Landmarks': [
      {name: 'Landmarks: Baldy Mountain', code: 'Landmarks__Baldy_Mou', description: 'Baldy Mountain, named for its rocky, barren top, is a favorite climb for those camping in the area at and around Baldy Town. Dotted with old gold mines, Baldy Mountain is the highest peak at Philmont, standing at 12,441 feet above sea level. The view from the top is unobstructed and spectacular.'},
      {name: 'Landmarks: Big Red', code: 'Landmarks__Big_Red', description: ''},
      {name: 'Landmarks: Black Jack\'s Hideout', code: 'Landmarks__Black_Jac', description: ''},
      {name: 'Landmarks: Black Mountain', code: 'Landmarks__Black_Mou', description: ''},
      {name: 'Landmarks: Comanche Peak', code: 'Landmarks__Comanche_', description: ''},
      {name: 'Landmarks: Hart Peak', code: 'Landmarks__Hart_Peak', description: ''},
      {name: 'Landmarks: Lookout Peak', code: 'Landmarks__Lookout_P', description: ''},
      {name: 'Landmarks: Lovers Leap Overlook', code: 'Landmarks__Lovers_Le', description: ''},
      {name: 'Landmarks: Mount Phillips', code: 'Landmarks__Mount_Phi', description: ''},
      {name: 'Landmarks: Scenic Hike', code: 'Landmarks__Scenic_Hi', description: ''},
      {name: 'Landmarks: Shaefers Peak', code: 'Landmarks__Shaefers_', description: ''},
      {name: 'Landmarks: T-Rex Track', code: 'Landmarks__T-Rex_Tra', description: ''},
      {name: 'Landmarks: Tooth of Time', code: 'Landmarks__Tooth_of_', description: 'Rising sharply 2,500 feet above the valley floor, the Tooth of Time stands at 9,003 feet and is one of Philmont’s most iconic landmarks. For travelers on the old Santa Fe Trail, this unmistakable rock formation signaled they were about two weeks from Santa Fe—and today, standing beneath or atop it, you’ll feel the same sense of arrival, scale, and history that has defined Philmont for generations.'},
      {name: 'Landmarks: Trail Peak', code: 'Landmarks__Trail_Pea', description: 'A hike up Trail Peak will give you the opportunity to visit the remains of the B-25 Liberator bomber that crashed here in 1942 killing all 7 crewmembers. Some of the wreckage remains, including a wing and propeller, and because of its location, it is the world\'s most visited airplane crash site.'},
      {name: 'Landmarks: Wilson Mesa', code: 'Landmarks__Wilson_Me', description: ''}
    ],
    'Livestock': [
      {name: 'Livestock: Animal Husbandry', code: 'Livestock__Animal_Hu', description: 'Abreu, Black Mountain, Crooked Creek, and Rich Cabins provide crews with the opportunity to learn how to care for farm animals the way early homesteaders did. These may include burros, cows, and chickens.'},
      {name: 'Livestock: Burro Packing', code: 'Livestock__Burro_Pac', description: 'No animal is more closely associated with the colorful history of the Southwest than the burro. Burro packing methods are explained and demonstrated at Ponil and Miranda. Your tents and food may be packed on burros using a diamond hitch. Burros are available for use on the trail in the northern portion of the ranch, starting or ending at Ponil and Miranda. Burro traps (holding pens for overnight stops) are located at Ponil, Pueblano, Miranda, Elkhorn, Flume Canyon, Head of Dean, and Baldy Skyline. Hay for feeding is provided at these camps. If your itinerary provides for packing burros, you will be able to pack them just as the miners once did. All crews on a burro itinerary must take a burro.'},
      {name: 'Livestock: Chicken Tending', code: 'Livestock__Chicken_T', description: 'The homesteaders that live at Abreu, Crooked Creek, and Rich Cabins raise chickens among other domestic animals. You will learn how to “harvest” eggs from the chicken coops and chase down the chickens when they escape!'},
      {name: 'Livestock: Goat Keeping', code: 'Livestock__Goat_Keep', description: ''},
      {name: 'Livestock: Horse Rides', code: 'Livestock__Horse_Rid', description: 'Philmont owns and maintains a remuda of 300 western horses with strings located at Beaubien, Clark’s Fork, and Ponil. All three camps offer exhilarating mountain horse rides at times noted on the crew\'s itinerary. Be prompt for your scheduled ride. Reservations are made at Logistics Services on a first-come, first-served basis when you arrive at Philmont. Persons weighing over 200 pounds will not be permitted to ride.'}
    ],
    'Range Sports': [
      {name: 'Range Sports: 3D Archery', code: 'Range_Sports__3D_Arc', description: 'More than shooting at flat targets, 3-D archery takes you along a trail with full-size animal targets set at different distances and angles. As your crew moves from station to station, you’ll test your skills, keep score, and see who can claim bragging rights as the best archer on the trail.'},
      {name: 'Range Sports: Aerial Archery', code: 'Range_Sports__Aerial', description: 'Using bows and arrows, you’ll shoot at foam targets launched into the air, testing your timing, focus, and accuracy. Each shot is fast-paced and exciting, and crews track their scores as they try to earn a spot on the camp’s high-score board for the summer.'},
      {name: 'Range Sports: Atlatl Throwing', code: 'Range_Sports__Atlatl', description: 'Learn to throw spears the way the ancient Ponil people once did. Using an atlatl to launch your spear toward animal-shaped targets, you’ll test your accuracy and see how many “animals” you can bag to help feed your clan—some of them with surprising shapes and challenges.'},
      {name: 'Range Sports: Cartridge Reloading', code: 'Range_Sports__Cartri', description: 'In this hands-on program, you’ll learn how rifle cartridges are built from the ground up. Each participant reloads three .30-06 rounds and then fires them at Sawmill’s rifle range, connecting careful preparation with real shooting results.'},
      {name: 'Range Sports: Cowboy Action Shooting', code: 'Range_Sports__Cowboy', description: 'At Ponil, you’ll step straight into the Old West. Using single-action pistols, lever-action rifles, and coach shotguns, you’ll experience how cowboys once shot, loaded, and handled firearms in this fast-paced and unforgettable program.'},
      {name: 'Range Sports: Field Archery', code: 'Range_Sports__Field_', description: 'Also known as 3-D archery, this activity takes you outside with bows and arrows to shoot at full-size animal targets along a course. Each shot feels different as you judge distance, angle, and accuracy in a realistic outdoor setting.'},
      {name: 'Range Sports: Muzzleloader Shooting', code: 'Range_Sports__Muzzle', description: 'At Black Mountain, Clear Creek, or Miranda, you’ll load and fire a traditional muzzle-loading rifle using powder, patch, ball, ramrod, and cap. This program lets you experience the careful process and powerful payoff of shooting firearms from the early frontier era.'},
      {name: 'Range Sports: Rifle Shooting', code: 'Range_Sports__Rifle_', description: 'At Sawmill’s .30-06 rifle range, you’ll review firearm safety, shooting fundamentals, and wildlife conservation. Using metallic silhouette targets, you’ll test your focus and precision while learning how marksmanship connects to responsible game management.'},
      {name: 'Range Sports: Shotgun Shooting', code: 'Range_Sports__Shotgu', description: 'Shooting clay targets takes quick reactions and smooth timing. With instruction and practice, you’ll learn how to track and hit flying clay birds, discovering just how satisfying a well-placed shot can be.'},
      {name: 'Range Sports: Shotshell Reloading', code: 'Range_Sports__Shotsh', description: 'You’ll reload three 12-gauge shotgun shells and then fire them at Harlan’s shotgun range. This program shows how attention to detail and careful assembly translate directly into success on the range.'},
      {name: 'Range Sports: Tomahawk Throwing', code: 'Range_Sports__Tomaha', description: 'Grip a tomahawk and test your skill by throwing it at wooden targets. While throwing is easy, getting the blade to stick takes practice, focus, and technique as you compete against your crewmates for bragging rights.'}
    ],
    'STEM': [
      {name: 'STEM: Archeology', code: 'STEM__Archeology', description: 'The Ponil country in the northern section is rich in the prehistoric background of the American Indian. Your crew can help reconstruct Philmont history while participating in this fascinating program and learning about Indians who inhabited this area. You can visit the site of a well-preserved Tyrannosaurus Rex footprint. This is the world’s only confirmed fossil footprint of a T-Rex.'},
      {name: 'STEM: Astronomy', code: 'STEM__Astronomy', description: 'Learn about our solar system up close and personal. Gaze through a professional quality telescope to see the rings of Saturn, distant stars, and moons.'},
      {name: 'STEM: Geology', code: 'STEM__Geology', description: 'Philmont staff and volunteer geologists have teamed up to provide an exciting and educational program of geology and mining technology at sites where history comes alive.'}
    ],
    'Western Lore': [
      {name: 'Western Lore: Branding', code: 'Western_Lore__Brandi', description: 'In this program, you’ll step into the world of working ranches and learn how cattle were marked and managed on the open range. Through demonstration and stories, you’ll see how branding identified ownership, prevented rustling, and played a key role in the ranching traditions that shaped life in the American West.'},
      {name: 'Western Lore: Cantina', code: 'Western_Lore__Cantin', description: 'Abreu and Ponil offer the opportunity for a thirst-quenching root beer in a Mexican or Western-style cantina. You can buy root beer for your whole crew or a cup for yourself.'},
      {name: 'Western Lore: Roping', code: 'Western_Lore__Roping', description: 'In this hands-on program, you’ll learn the basics of roping the way working cowboys did on the open range. Practicing your throw and timing, you’ll see how skill with a rope was essential for handling cattle and why roping became such an iconic part of Western life.'}
    ],
    'Wheeled': [
      {name: 'Wheeled: Mountain Biking', code: 'Wheeled__Mountain_Bi', description: 'Enjoy one of America’s fastest growing sports while you are camped at Ring Place. You will visit Whiteman Vega Camp as your crew takes a wilderness mountain bike ride into the most remote areas of the beautiful Valle Vidal section of the Carson National Forest. You will learn bike maintenance, riding techniques, and bike trail construction.'}
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
      
      // Build help text with description if available
      var helpText = 'Rate from 0 (No Interest) to 20 (Very High Interest)';
      if (program.description && program.description.trim() !== '') {
        helpText += '\n' + program.description;
      }
      
      programItem.setTitle(program.name)
        .setChoices(choices)
        .setHelpText(helpText)
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