@void
Feature: Void
    Covers voids and fillings.

Scenario: Add an opening
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And the object "IfcWall/Cube" is selected
    And additionally the object "Cube" is selected
    When I press "bim.add_opening"
    Then the object "Cube" does not exist
    And the object "IfcWall/Cube" is voided by "Cube"

Scenario: Add an opening using the BIM tool
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    When I press "bim.add_opening"
    Then the object "Opening" does not exist
    And the object "IfcWall/Cube" is voided by "Opening"

Scenario: Show openings
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"
    And the object "IfcWall/Cube" is selected
    When I press "bim.show_openings"
    Then the object "IfcOpeningElement/Opening" is an "IfcOpeningElement"
    And the object "IfcWall/Cube" is voided by "Opening"

Scenario: Hide openings
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"
    And the object "IfcWall/Cube" is selected
    And I press "bim.show_openings"
    When I press "bim.hide_openings"
    Then the object "IfcOpeningElement/Opening" does not exist

Scenario: Edit openings
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"
    And the object "IfcWall/Cube" is selected
    And I press "bim.show_openings"
    When the object "IfcOpeningElement/Opening" is moved to "1,0,0"
    And I press "bim.edit_openings"
    Then the object "IfcOpeningElement/Opening" does not exist
    And the object "IfcWall/Cube" is voided by "Opening"

Scenario: Add an opening to Element B with a void that already voids Element A
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"

    And I add a cube
    And the object "Cube" is selected
    And I press "bim.assign_class"

    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"

    And the object "IfcWall/Cube" is selected
    And I press "bim.show_openings"

    When the object "IfcOpeningElement/Opening" is selected
    And additionally the object "IfcWall/Cube.001" is selected
    And I press "bim.add_opening"

    Then the object "IfcWall/Cube" is not voided by "Opening"
    And the object "IfcWall/Cube.001" is voided by "Opening"

Scenario: Remove opening
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"
    And the object "IfcWall/Cube" is selected
    And I press "bim.show_openings"
    When the object "IfcOpeningElement/Opening" is selected
    And the variable "opening_id" is "IfcStore.get_file().by_type('IfcOpeningElement')[0].id()"
    And I press "bim.remove_opening(opening_id={opening_id})"
    Then the object "Opening" is not an IFC element
    And the object "IfcWall/Cube" is not voided by "Opening"

Scenario: Remove opening - using deletion
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"
    And the object "IfcWall/Cube" is selected
    And I press "bim.show_openings"
    When the object "IfcOpeningElement/Opening" is selected
    And I delete the selected objects
    Then the object "Opening" does not exist
    And the object "IfcWall/Cube" is not voided by "Opening"

Scenario: Remove opening - indirectly by deleting its building element
    Given an empty IFC project
    And I add a cube
    And the object "Cube" is selected
    And I look at the "Class" panel
    And I set the "Products" property to "IfcElement"
    And I set the "Class" property to "IfcWall"
    And I click "Assign IFC Class"
    And I add a cube
    And I rename the object "Cube" to "Opening"
    And the object "Opening" is selected
    And additionally the object "IfcWall/Cube" is selected
    And I press "bim.add_opening"
    And the object "IfcWall/Cube" is selected
    And I press "bim.show_openings"
    When the object "IfcWall/Cube" is selected
    And I delete the selected objects
    Then the object "IfcOpeningElement/Opening" does not exist
