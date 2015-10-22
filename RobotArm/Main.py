import math
import cv2
import Common
import Robot
import CheckersAI
import Variables as V
from Video import Vision
from Video import ImageStitching
from  time import sleep

from threading import Thread



# #DEPRECATED FUNCTIONS (REPLACE SOON)
# def pickUpTarget(target):
#     print "pickUpTarget(target) THIS FUNCTION IS DEPRECATED, remove soon!"
#     #SET UP
#     currentPosition = Robot.getPosArgsCopy()  #Records position to return to after picking up object
#     targetFocus = [screenDimensions[0] / 2 - V.pixFromCamToArm, screenDimensions[1] / 2]
#     focusOnTarget(target, targetFocus = targetFocus)
#     focusOnTargetManual(target, targetFocus = targetFocus)
#
#     Robot.moveTo(height = (V.heightMax + 60) / 4, waitForRobot = True, relative = False)
#     focusOnTargetManual(target, targetFocus = targetFocus)
#
#     #DESCEND ONTO OBJECT
#     while Robot.getOutput('touch')["touch"] == 1:
#         if Robot.pos["height"]-V.heightMin > 30:
#             Robot.moveTo(height = -30)
#         else:
#             Robot.moveTo(height = Robot.pos["height"] + V.heightMin)
#
#     Robot.setGrabber(1)              #Grab
#     Robot.moveTo(relative = False, **currentPosition)  #Return to original position
#
# def focusOnTargetManual(target, **kwargs):  #Arguments: targetFocus (The pixel location where you want the target to be alligned. Default is the center of the screen
#     print "focusOnTargetManual() THIS FUNCTION IS DEPRECATED, remove soon!"
#     targetFocus = kwargs.get('targetFocus', [screenDimensions[0] / 2, screenDimensions[1] / 2])  #The XY value of WHERE on the screen we want the robot to focus on.
#     moveIncrement = 3
#     while True:  #Robot arm will slowly approach the target`
#         coords = objTracker.getTargetCenter(target)
#         if len(coords) == 0: continue  #DO NOT MOVE. Prevents empty coords from continuing.
#         xMove = 0
#         yMove = 0
#         if not Common.isWithinTolerance(coords[0], targetFocus[0]):
#             if coords[0] < targetFocus[0]: xMove   -= moveIncrement
#             if coords[0] > targetFocus[0]: xMove   += moveIncrement
#         if not Common.isWithinTolerance(coords[1], targetFocus[1]):
#             if coords[1] < targetFocus[1]: yMove   -= moveIncrement
#             if coords[1] > targetFocus[1]: yMove   += moveIncrement
#         if Common.isWithinTolerance(coords[1], targetFocus[1]) and Common.isWithinTolerance(coords[0], targetFocus[0]):
#             break  #Once the target has been focused on, quit
#         Robot.moveTo(x = xMove, y = -yMove)
#
#



#GENERIC FUNCTIONS
def focusOnTarget(getTargetCoords, **kwargs):
    """
    :param getTargetCoords: FOCUSES ON TARGET
    :param kwargs:
        "targetFocus":  (Default [screenXDimension, screenYdimension]) HOLDS AN ARRAY THAT TELLS YOU WHERE ON THE SCREEN TO FOCUS THE OBJECT
        "tolerance":    (defaults to Variables default) How many pixels away till the object is considered "focused" on.
        "ppX":          (Default -1) The amount of pixels that one "stretch" move of the robot will move. This changes according to what height the robot is at
                                    Which is the reason it is even adjustable. If this is not put in, the robot will target very slowly, but be most likely
                                    to reach the target. So you are trading reliability (at all heights) for speed at a specific situation. Same for ppY, except
                                    relating to the "rotation" movement of the robot.
        "ppY":          (Default -1)
    :return: THE ROBOT WILL HAVE THE OBJECT FOCUSED ON THE PIXEL OF TARGETFOCUS

    RECOMMENDED ppX and ppY VALUES FOR DIFFERENT HEIGHTS:
        HEIGHT = MAX: ppX = 3,    ppY = 12  (avg 3-4 moves)
        HEIGHT = 70:  ppX = 3.75  ppY = 15  (avg 2-4 moves)
        HEIGHT = 0:   ppx = 5.3   ppy = 38  (avg 3-5 moves)
    """

    ppX         = kwargs.get("ppX", -1)  #Pixels per X move
    ppY         = kwargs.get("ppY", -1)   #Pixels per Y move
    targetFocus = kwargs.get("targetFocus", [screenDimensions[0] / 2, screenDimensions[1] / 2])   #The XY value of WHERE on the screen we want the robot to focus on.
    tolerance   = kwargs.get("tolerance", 15)
    maxMoves    = kwargs.get("maxMoves", 40)
    sign        = lambda x: (1, -1)[x < 0]  #sign(x) will return the sign of a number'
    moveCount   = 0  #The amount of moves that it took to focus on the object

    while True:  #Robot arm will slowly approach the target
        try:
            coords = getTargetCoords()
        except NameError as e:
            print "ERROR: focusOnTarget(", locals().get("args"), "): error (", e, "). Object not found. Leaving Function..."
            raise  #RE-Raise the exception for some other program to figure out

        distance = ((coords[0] - targetFocus[0]) ** 2 + (coords[1] - targetFocus[1]) ** 2) ** 0.5  #For debugging
        xMove = float(0)
        yMove = float(0)
        yDist = targetFocus[0] - coords[0]
        xDist = targetFocus[1] - coords[1]
        if abs(xDist) > .85 * tolerance:  #I am stricter on x tolerance, bc the robot has more x incriments for movement.
            xMove  = sign(xDist) * .5
            xMove += sign(xDist) * 3 * (abs(xDist) > tolerance * 5 and     ppX == -1)  #If far from the target, then move a little faster
            xMove += (xDist / ppX)   * (abs(xDist) > tolerance     and not ppX == -1)  #If a pp? setting was sent in kwArgs, then perform it.
        if abs(yDist) > tolerance:
            yMove  = sign(yDist) * .5
            yMove += sign(yDist) * 3 * (abs(yDist) > tolerance * 5 and     ppY == -1)
            yMove += (yDist / ppY)   * (abs(yDist) > tolerance     and not ppY == -1)

        #print "focusOnTarget(", locals().get("args"), "): xMove: ", xMove, "yMove: ",  yMove
        if not (int(xMove) == 0 and int(yMove) == 0):
            moveCount += 1
            Robot.moveTo(y = yMove, x = xMove)  #TODO: make a variable that flips these around according to orientation of camera
            #print Robot.getPosArgsCopy()
            if yDist < tolerance * 2 or xDist < tolerance * 1.25:  #Slow down a bit when approaching the target
                sleep(.3)
            else:
                sleep(.1)

            if Robot.pos["stretch"] == Robot.stretchMax or Robot.pos["stretch"] == Robot.stretchMin:
                print "focusOnTarget(", locals().get("args"), "): Object out of Stretching reach."
                break
            if Robot.pos["rotation"] == Robot.rotationMax or Robot.pos["rotation"] == Robot.rotationMin:
                print "focusOnTarget(", locals().get("args"), "): Object out of Rotating reach."
                break
            if moveCount >= maxMoves:
                raise Exception("TooManyMoves")

        else:
            print "focusOnTarget(", locals().get("args"), "): Object Targeted in ", moveCount, "moves."
            break

def focusOnCoord(coords, **kwargs):  #Arguments: targetFocus (The pixel location where you want the target to be alligned. Default is the center of the screen
    targetFocus = kwargs.get('targetFocus', [screenDimensions[0] / 2, screenDimensions[1] / 2])
    if len(coords) == 0:
        print "Trouble focusing on coord:", coords
        return
    diffX = coords[0] - targetFocus[0]
    diffY = coords[1] - targetFocus[1]
    #ratio = (Robot.pos['height'] + 60.0) / (Robot.heightMax + 60.0)
    #print Robot.pos['height']
    #ratio = 1  #for not, while I get THAT working...
    xMove = (diffX / (V.pixelsPerX ))
    yMove = (diffY / (V.pixelsPerY  ))
    print "Xmove: ", xMove, "Ymove: ", yMove
    Robot.moveTo(rotation = yMove / 2, stretch = xMove * 2, waitForRobot = True)
    #Robot.moveTo(x = xMove, y = -yMove, waitForRobot = True)

def calibrateRobotCamera(target):
    """
        Figures out important variables for the robot from a series of trials and repeats and then averaging the result
    avgPixelPerX    Using cartesian coordinates, how many pixels (at max height) does an object move per unit x move of the robot?
    avgPixelPerY    Same as above, but for y
    """
    xToMove             = 110.0   #How many degrees to turn during the rotation test.
    yToMove             = 75.0   #How many 'units' to stretch
    avgPixelPerX        = 0.0
    avgPixelPerY        = 0.0
    #Robot.moveTo(height = 90, relative = False, wiatForRobot = True)#(V.heightMax - V.heightMin) / 2)
    for x in range(0, V.trialsForCalibration):
        focusOnTargetManual(target)

        #X CALIBRATION: GO TO COORD 1
        Robot.moveTo(x = xToMove / 2, waitForRobot = True)
        coords1 = objTracker.getTargetAvgCenter(target, V.framesForCalibration)
        #GO TO COORD 2
        Robot.moveTo(x = -xToMove, waitForRobot = True)
        coords2 = objTracker.getTargetAvgCenter(target, V.framesForCalibration)
        #GO TO COORD 3
        Robot.moveTo(x = xToMove, waitForRobot = True)
        coords3 = objTracker.getTargetAvgCenter(target, V.framesForCalibration)

        Robot.moveTo(x = -xToMove / 2)                       #Return robot
        avgPositiveX =  (coords2[0] - coords1[0]) / xToMove
        avgNegativeX =  (coords2[0] - coords3[0]) / xToMove
        avgPixelPerX += (avgPositiveX + avgNegativeX) / 2.0
        print 'Avg Positive X: %s' % avgPositiveX
        print 'Avg Negative X: %s' % avgNegativeX

        #Y CALIBRATION: GO TO COORD 1
        focusOnTargetManual(target)
        Robot.moveTo(y = yToMove / 2, waitForRobot = True)
        coords1 = objTracker.getTargetAvgCenter(target, V.framesForCalibration)
        #GO TO COORD 2
        Robot.moveTo(y = -yToMove, waitForRobot = True)
        coords2 = objTracker.getTargetAvgCenter(target, V.framesForCalibration)
        #GO TO COORD 3
        Robot.moveTo(y = yToMove, waitForRobot = True)
        coords3 = objTracker.getTargetAvgCenter(target, V.framesForCalibration)

        Robot.moveTo(y = -yToMove / 2)                       #Return robot
        avgPositiveY =  (coords1[1] - coords2[1]) / yToMove
        avgNegativeY =  (coords3[1] - coords2[1]) / yToMove
        avgPixelPerY += (avgPositiveY + avgNegativeY) / 2.0

        print 'Avg Positive Y: %s' % avgPositiveY
        print 'Avg Negative Y: %s' % avgNegativeY

    print 'Calibration over'
    return avgPixelPerX / V.trialsForCalibration, avgPixelPerY / V.trialsForCalibration

def waitTillStill(**kwargs):
    maxTime     = kwargs.get("timeout", 1)  #If it goes over maxTime seconds, the function will quit
    maxMovement = kwargs.get("movement", 8)
    if maxMovement <= 5:
        print "waitTillStill(", locals().get("args"), "): It is unwise to set the movement parameter to < than 4. It is set at ", maxMovement

    timer = Common.Timer(maxTime)  #Will wait one second max before continuing
    while objTracker.getMovement() > maxMovement:
        if timer.timeIsUp():
            print "waitTillStill(", locals().get("args"), "): Timer has timed out. Consider lowering acceptableMovement. Continuing...", objTracker.getMovement()
            break



def getAngle(quad):
    """
    :param quad: The 4 coordinate point array
    :return: Returns the angle of the block in the long side, which can be used to orient the wrist of the robot.
    """
    side1 = ((quad[0][0] - quad[1][0]) ** 2.0 + (quad[0][1] - quad[1][1]) ** 2.0) ** 0.5
    side2 = ((quad[1][0] - quad[2][0]) ** 2.0 + (quad[1][1] - quad[2][1]) ** 2.0) ** 0.5
    if side2 < side1:
        angle = math.atan((quad[0][1] - quad[1][1]) * 1.0 / (quad[0][0] - quad[1][0]) * 1.0)
    else:
        angle = math.atan((quad[1][1] - quad[2][1]) * 1.0 / (quad[1][0] - quad[2][0]) * 1.0 )

    angle = math.degrees(angle)
    return angle



###########  JENGA FUNCTIONS ###########
def stackJenga():
  #Main Function
    print "Playing Jenga!"
    #SET UP VARIABLES AND RESET ROBOT POSITION
    blocks = (1, 0, 2)  #The order to place the blocks
    markerLKP = {"rotation": 30, "stretch": 100}  #Keep track of the "marker block"'s "Last Known Position" (LKP)
    searchPos = {'rotation': -15, 'stretch': Robot.stretchMax / 2.5, 'height': Robot.heightMax, 'wrist': 0}
    originalMarker = markerLKP.copy()
    originalSearchPos = searchPos.copy()
    Robot.moveTo(relative = False, waitForRobot = True, **searchPos)  #Get robot in position before testing movementConstant
    movementConstant = (isObjectGrabbed() + isObjectGrabbed() + isObjectGrabbed()) / 3  #Get an average of how much movement there is when there is no block


    for l in (1, 2, 3, 4, 5):  #For each layer
        #FIND A BLOCK, PICK UP THE BLOCK, AND PLACE IT IN THE CORRECT SPOT
        b = 0  #Current block you are putting. THE ORDER IS IN THE "blocks" ARRAY, HOWEVER!!!

        while b in blocks:  #Blocks to place, in order
            print "stackJenga(XXX): Currently on layer ", l, " and on block ", b

            #GO TO POSITION FOR SEARCHING FOR BLOCKS, BUT DO IT SLOWLY AS TO NOT MOVE ROBOT'S BASE
            sleep(.2)
            Robot.moveTo(relative = False, waitForRobot = True, **searchPos)


            #START SEARCHING FOR BLOCKS
            while len(objTracker.getShapes(4)) == 0:  #Search for a view that has a block in it
                if Robot.pos["rotation"] > -69:
                    Robot.moveTo(rotation = -10)
                    waitTillStill()
                else:
                    print "stackJenga(", locals().get("args"), "): No shapes found after one sweep."
                    searchPos = originalSearchPos.copy()
                    Robot.moveTo(rotation = -15, stretch = V.stretchMax / 2.5, height = V.heightMax, relative = False)  #Go back and sweep again
            searchPos = {"rotation": Robot.pos["rotation"], "stretch": V.stretchMax / 2.5, "height": V.heightMax}


            #PICK UP A BLOCK
            try:
                pickUpBlock(movementConstant, Robot.getPosArgsCopy())  #IF pickUpBlock() FAILS 3 ATTEMPTS, RESTART THIS FOR LOOP
            except Exception as e:
                Robot.setGrabber(0)
                print "ERROR: stackJenga(XXX): ", e, " while picking up block. Restarting for loop and attempting again.."
                continue  #Since b never got upped one, then there is no harm in using continue


            #MOVE TO, FOCUS ON, AND RECORD NEW POSITION, OF THE MARKER BLOCK
            Robot.moveTo(rotation = markerLKP["rotation"] / 2, height = 70, relative = False)
            sleep(.2)
            Robot.moveTo(rotation = markerLKP["rotation"], stretch = markerLKP["stretch"], height = 70, relative = False, waitForRobot = True)
            waitTillStill()
            error = False

            if len(objTracker.getShapes(4)) == 0:  #If marker not seen in the middle, go to the right and check for it
                Robot.moveTo(rotation = markerLKP["rotation"] + 10, stretch = 100, relative = False, waitForRobot = True)
            if len(objTracker.getShapes(4)) == 0:  #If marker still not to the right, move to the left and check for it
                Robot.moveTo(rotation = markerLKP["rotation"] - 10, stretch = 100, relative = False, waitForRobot = True)

            if len(objTracker.getShapes(4)) > 0:  #If the marker HAS been seen, then focus on it.
                try:
                    targetFocus = [screenDimensions[0] * .75, screenDimensions[1] / 2]  #The right edge of the screen
                    focusOnTarget(lambda: objTracker.bruteGetFrame(lambda: objTracker.getNearestShape(4, nearestTo = targetFocus ).center), targetFocus = targetFocus, tolerance = 9, **{"ppX": 3.7, "ppY": 15})
                    print "stackJenga(XXX): Successfully focused on marker block"
                except Exception as e:
                    print "ERROR: stackJenga(XXX): ", e, " while searching for marker."
                    error = True
            else:
                error = True  #If the marker has NOT been seen, catch it right below
            if error:  #If the robot messed up either focusing on the object or having never seen it, then...
                print "stackJenga(XXX): Failed too many times searching for marker. Placing current off to the side, RESETTING markerLKP"
                placeBlock(searchPos, 0, 0)
                markerLKP = originalMarker.copy()
                continue
            waitTillStill()


            #RECORD NEW ADJUSTED "LAST KNOWN POSITION" OF markerLKP, THROUGH AN AVG OF LAST AND CURRENT.
            if abs(Robot.pos["rotation"] - markerLKP["rotation"]) < 20 and abs(Robot.pos["stretch"] - markerLKP["stretch"]) < 30 and not (l == 1 and b == 0):  #If the marker is in a semi-valid position, then RECORD that position. (used to be a big issue)
                markerLKP = {"rotation": (markerLKP["rotation"] + Robot.pos["rotation"]) / 2, "stretch": (markerLKP["stretch"] + Robot.pos["stretch"]) / 2}  #Get avg of last known position and new known position (messes things up less)
                print "stackJenga(XXX): New location of markerLKP: ", markerLKP  #Print new location of the marker
            else:
                print "stackJenga(XXX): SOMETHINGS GONE WRONG with markerLKP! markerLKP: ", markerLKP


            #PLACE BLOCK ONTO THE CORRECT POSITION ON THE STACK
            placeBlockAtPosition(l, blocks[b])
            b += 1  #Mark block on layer as completed, so for loop will move on to next block.

    #MISSION COMPLETE! INITIATE DANCE SEQUENCE!
    Robot.moveTo(relative = False, **Robot.home)
    sleep(.6)
    Robot.moveTo(rotation = -30)
    sleep(.3)
    Robot.moveTo(rotation = 30)
    sleep(.3)
    Robot.moveTo(height = 0)
    sleep(.3)
    Robot.moveTo(height = Robot.heightMax)
    sleep(.3)

def pickUpBlock(movConstant, objectLastSeen, **kwargs):
    """
    Robot will attempt to pick up block. If it fails, it will RECURSIVELY attempt to pick it up again from the last known position. kwarg "attempts" is used to cut off the robot after
    the 3rd (configurable) attempt.
    :param movementConstant: this is the average pixel change per frame when the robot is stationary and there is no jenga block in it's grabber when the grabber moves.
                            It is used with isObjectGrabbed to detect if the robot successfuly grabbed a jenga block
    :param startingPos:     Self explanatory. String of robot position, from where to start
    :return:
    kwargs:
        attempts: Counts how many times before this program has run itself recursively, in order to determine if it should stop attempting and return an error.
        attemptRefocus: (Defaults to true). If this is true, the robot will attempt to refocus on the block using a different manner if it is >50 or <-50 degrees position.
    """
    attempts = kwargs.get("attempts", 0)                                                                            #Total times this func has been run recursively (at 3, it raises an error)
    attemptRefocus = kwargs.get("attemptRefocus", True)                                                             #Should robot attempt to do fancy refocusing on certain blocks
    targetCenter = [screenDimensions[0] / 2, screenDimensions[1] / 2]                                               #Target center of screen
    heightSettings = {"150": {"ppX": 3, "ppY": 12}, "70": {"ppX": 3.7, "ppY": 15}, "0": {"ppX": 5.3, "ppY": -1}}    #Holds the best ppX ppY settings for different heights.
    getShapeCenter = lambda: objTracker.bruteGetFrame(lambda: objTracker.getNearestShape(4).center)                 #This function is used a lot, so it was useful to save as a variable.

    #CHECK IF THIS FUNCTION HAS BEEN RUN RECURSIVELY MORE THAN THE SET LIMIT, AND QUIT IF IT HAS
    print "pickUpBlock(", locals().get("args"), "): Attempt number: ", attempts
    if attempts == 3:  #If max attempts have been hit
        print "pickUpBlock(", locals().get("args"), "): Too many recursive attempts. Raising error"
        raise Exception("BlockNotGrabbed")


    #GET ROBOT INTO POSITION AND CHECK IF THE OBJECT IS STILL THERE. QUIT IF IT IS NOT.
    waitTillStill()
    Robot.setGrabber(0)
    Robot.moveTo(relative = False, **objectLastSeen)
    waitTillStill()
    sleep(.1)
    if len(objTracker.getShapes(4)) == 0:  #If no objects in view
        print "pickUpBlock(", locals().get("args"), "): No objects seen at start. Raising error..."
        raise NameError("ObjNotFound")


    #BEGIN FOCUSING PROCESS UNTIL ROBOT IS AT 0 HEIGHT AND COMPLETELY FOCUSED ON OBJECT
    try:
        if Robot.pos["height"] == 150:
            print "pickUpBlock(", locals().get("args"), "): Focus at height 150"
            objectLastSeen = Robot.getPosArgsCopy(dontRecord = ["wrist, grabber, height"])
            focusOnTarget(getShapeCenter, **heightSettings["150"])  #Tries many times (brute) to get the nearest shapes .center coords & focus
            objectLastSeen = Robot.getPosArgsCopy(dontRecord = ["wrist, grabber, height"])
            Robot.moveTo(height = 70, relative = False)
            waitTillStill()

        if Robot.pos["height"] == 70:
            print "pickUpBlock(", locals().get("args"), "): Focus at height 70"
            focusOnTarget(getShapeCenter, **heightSettings["70"])
            objectLastSeen = Robot.getPosArgsCopy(dontRecord = ["wrist, grabber, height"])
            Robot.moveTo(height = 0, relative = False)
            waitTillStill()

        if Robot.pos["height"] == 0:
            print "pickUpBlock(", locals().get("args"), "): Focus at height 0"
            focusOnTarget(getShapeCenter,  tolerance = 7, **heightSettings["0"])
            objectLastSeen = Robot.getPosArgsCopy(dontRecord = ["wrist, grabber, height"])

        shape = objTracker.bruteGetFrame(lambda: objTracker.getNearestShape(4)).vertices
    except NameError as e:
        print "ERROR: pickUpBlock(", locals().get("args"), "): ", e
        pickUpBlock(movConstant, objectLastSeen, attempts = attempts + 1)
        return False
        #raise Exception("PickupFailed")


    #IF THE OBJECT IS > 50 OR < -50 DEGREES, DO ANOTHER ROUND OF FOCUSING ON IT, AND PERFORM A DIFFERENT "DROP DOWN" MANUEVER
    angle = getAngle(shape)  #Get angle of object in camera
    if (angle > 50 or angle < -50) and attemptRefocus:
        try:
            print "pickUpBlock(", locals().get("args"), "): Performing re-focusing manuever on block of angle: ", angle
            targetFocus = [screenDimensions[0] / 3.5, screenDimensions[1] / 2]
            focusOnTarget(lambda: objTracker.bruteGetFrame(lambda: objTracker.getNearestShape(4, nearestTo = targetFocus).center),  tolerance = 8, targetFocus = targetFocus, **heightSettings["0"])
            objectLastSeen = Robot.getPosArgsCopy(dontRecord = ["wrist, grabber, height"])
        except NameError as e:  #Since it failed, try again but this time send the function a "normalPickup = True", so it won't attempt to do it again
            print "ERROR: pickUpBlock(", locals().get("args"), "): ", e, " when trying to RE-FOCUS on a >50 <-50 block"
            pickUpBlock(movConstant, objectLastSeen, attempts = attempts + 1, attemptRefocus = False)
            return False

        #MOVE SO OBJECT IS UNDER GRABBER
        Robot.moveTo(height = -05, relative = False)  #Ease into it
        waitTillStill()
        Robot.moveTo(stretch = 26)
        waitTillStill()

    else:
        #MOVE SO OBJECT IS UNDER GRABBER
        Robot.moveTo(stretch = 52, rotation = 2.25)  #Added a rotation to fix weird issues that had been occurring...
        waitTillStill()


    #MOVE WRIST, AND DESCEND ONTO OBJECT AND PICK IT UP
    Robot.moveTo(wrist = angle, height = -20, relative = False)
    sleep(.075)
    Robot.moveTo(height = -38, relative = False)
    sleep(.05)
    Robot.setGrabber(1)  #Pick up object
    sleep(.125)
    Robot.moveTo(height = -5, relative = False)
    sleep(.2)


    #MEASURE THE MOVEMENT OF THE OBJECT AS THE WRIST MOVES
    Robot.moveTo(wrist = -40, relative = False)  #Start rotating the wrist
    Robot.moveTo(wrist = 20, relative = False)
    timer = Common.Timer(.4)
    highestMovement = 0
    while not timer.timeIsUp():  #Gets the highest measured movement in .3 seconds, to DEFINITELY catch the wrist moving. Eliminates problems.
        newMovement = objTracker.getMovement()
        if newMovement > highestMovement: highestMovement = newMovement
        if highestMovement > movConstant + 1.5: break
    print "pickUpBlock(", locals().get("args"), "): highestMovement: ", highestMovement


    #IF MOVEMENT IS < MOVCONSTANT, THEN NO OBJECT WAS PICKED UP. RE-RUN FUNCTION.
    if highestMovement < movConstant + 3:
        print "pickUpBlock(", locals().get("args"), "): Failed to suck in object. Retrying..."
        pickUpBlock(movConstant, objectLastSeen, attempts = attempts + 1, attemptRefocus = not attemptRefocus)
        return False

    Robot.moveTo(wrist = 0, relative = False)  #Return wrist
    return True

def isObjectGrabbed():
    currentWrist = Robot.pos["wrist"]
    Robot.moveTo(wrist = -40, relative = False)
    Robot.moveTo(wrist = 20, relative = False)
    sleep(.01)
    movement = objTracker.getMovement()

    Robot.moveTo(wrist = currentWrist, relative = False)
    print "isObjectGrabbed(", locals().get("args"), "): Movement = ", movement
    return movement

def placeBlock(position, height, wrist):
    currentPosition = Robot.getPosArgsCopy()
    Robot.moveTo(rotation = position["rotation"], stretch = position["stretch"], relative = False)  #GET IN POSITION OVER DROP ZONE
    Robot.moveTo(height = height, wrist = wrist, waitForRobot = True, relative = False)
    Robot.setGrabber(0)
    Robot.moveTo(height = currentPosition["height"], relative = False)
    Robot.moveTo(relative = False, **currentPosition)

def placeBlockAtPosition(layer, position):
    """
    FOR THE TOWER BUILDING. Aligns the brick to either a horizontal or vertical position, determined mathematically by the "layer" variable.
    The "layer" variable determines the height.
    The "position" variable is a string- it is either 0, 1, 2 determining where on the current layer of the tower (1 = left, 2 = middle, or something akin).
    that the brick should go on.
    :param layer: Layer on the building. Starts at 1. 1st layer is horizontal.
    :param position: "right", "left
    :return: A brick placed
    """
    #SET UP VARIABLES
    currentPosition = Robot.getPosArgsCopy()  #Back up the position in case of error
    heightForLayer = {"1": -32, "2": -15, "3": 3, "4": 24, "5": 40.5}
    print "placeBlockAtPosition(", locals().get("args"), "): Current pos: ", currentPosition

    #PICK THE RELEVANT MOVEMENTS FOR EACH LAYER/POSITION, AND PERFORM IT
    if not layer % 2:  #IF THIS IS THE VERTICAL LAYER
        print "PLACING DOWN VERTICAL BLOCK ON POSITION ", position, "ON LAYER ", layer
        #HOW MUCH STRETCH / ROTATION IS NECESSARY FOR EACH POSITION. [POSITION]
        rotToMoveSide     = [19,  0, -19]
        rotToMoveSlip     = [-12, 0,   10]
        stretchToMove     = [-2,  0,  -2]  #Adjust the angle so it is truly vertical.
        wristToMove       = [-10, 0,  10]
        Robot.moveTo(height = heightForLayer[str(layer)] + 34, wrist = wristToMove[position], relative = False)  #Move Wrist BEFORE going all the way down, or else you might knock some blocks
        Robot.moveTo(rotation =  rotToMoveSide[position], stretch = stretchToMove[position])  #Go besides (but offset) to the end position of the block
        sleep(.1)
        Robot.moveTo(height = heightForLayer[str(layer)], relative = False)  #Finish going down
        waitTillStill()
        Robot.moveTo(rotation = rotToMoveSlip[position] * .75)  #Slip block in to the correct position sideways (Hopefully pushing other blocks into a better position
        sleep(.1)
        Robot.moveTo(rotation = rotToMoveSlip[position] * .25)  #Slip block in to the correct position sideways (Hopefully pushing other blocks into a better position

    else:           #IF THIS IS THE HORIZONTAL LAYER
        stretchToMoveSide = [-45, 0, 49]  #To get parallel to the part
        stretchToMoveSlip = [25, 0, -25]  #To slip it in all the way
        wristToMove = 73.5  #Equivalent to 90 degrees, for some reason
        Robot.moveTo(height = heightForLayer[str(layer)] + 34, wrist = wristToMove, relative = False)  #Move Wrist BEFORE going all the way down, or else you might knock some blocks
        Robot.moveTo(stretch = stretchToMoveSide[position])
        sleep(.1)
        Robot.moveTo(height = heightForLayer[str(layer)], relative = False)  #Finish going down
        waitTillStill()
        Robot.moveTo(stretch = stretchToMoveSlip[position] * .75)  #Ease into the correct position by splitting it into two moves
        sleep(.1)
        Robot.moveTo(stretch = stretchToMoveSlip[position] * .25)

    #DROP BRICK AND GO BACK TO ORIGINAL POSITION
    sleep(.1)
    print Robot.pos
    Robot.setGrabber(0)
    Robot.moveTo(height = currentPosition["height"], relative = False)
    sleep(.2)
    Robot.moveTo(relative = False, **currentPosition)
    waitTillStill()



########### Checkers FUNCTIONS ###########
def playCheckers():
    global streamVideo
    streamVideo = True
    cornerLocations = getBoardCorners()

    redThreshold = 0     #Used to measure what piece is pink and what piece is green. This constant is set later on using getAverageColor()
    firstLoop    = True  #This will tell the robot to calibrate the average color on the first round of the game.
    AI = CheckersAI.DraughtsBrain({'PIECE':    15,  #Checkers AI class. These values decide how the AI will play
                                   'KING':     30,
                                   'BACK':      3,
                                   'KBACK':     3,
                                   'CENTER':    6,
                                   'KCENTER':   7,
                                   'FRONT':     6,
                                   'KFRONT':    3,
                                   'MOB':     6}, 5)

    while not exitApp:
        #stitchedFrame = cv2.imread("F:\Google Drive\Projects\Git Repositories\RobotStorage\RobotArm\stitched.png")

        #GET A STITCHED IMAGE THAT IS AN OVERVIEW OF THE BOARD AREA
        stitchedFrame = getBoardOverview(cornerLocations, finalImageWidth = 1000)

        #FIND THE BOARD IN THE STITCHED IMAGE
        shapeArray, edgedFrame = objTracker.getShapes(sides=4, peri=0.05,  minArea= (stitchedFrame.shape[0] * stitchedFrame.shape[1]) / 4,
                                                      threshHold=cv2.THRESH_OTSU, frameToAnalyze=stitchedFrame, returnFrame = True)
        if len(shapeArray) == 0:  #Make sure that the board was correctly found. If not, restart the loop and try again.
            print "__playCheckers()___: No board Found"
            continue

        #ISOLATE THE BOARD AND FIND THE CIRCLES IN IT
        warped = objTracker.getTransform(shapeArray[0], frameToAnalyze=stitchedFrame, transformHeight= 600, transformWidth=600)  #Isolate board
        circleArray = objTracker.getCircles(frameToAnalyze = warped, minRadius = 40)  #Get circles on screen

        #GET THE BOARD STATE AND PUSH IT THROUGH AN AI TO GET THE ROBOTS NEXT MOVE
        if firstLoop: redThreshold = getAverageColor(circleArray)[2]  #  If this is the first time being run, get the average color of the pieces on board
        boardState, warped = getBoardState(warped, circleArray, [600, 600], redThreshold)  #Find and label all circles with team, color, and location
        move = AI.best_move(board=boardState)  #Get the best possible move for the robot to perform
        print "From ", move.source[::-1], " to ", move.destination[::-1]

        #while True:
        #    column = float(raw_input("Row?: "))
        #    row = float(raw_input("Row?: "))
        #    Robot.moveTo(relative=False, **getSquarePosition(row, column, cornerLocations))

        #SET FRAMES FOR THE WINDOWS:
        vid.windowFrame["Main"]        = objTracker.drawShapes([shapeArray[0]], frameToDraw=stitchedFrame)
        vid.windowFrame["Perspective"] = objTracker.drawCircles(circleArray,    frameToDraw=warped)



        streamVideo = False
        raw_input("Press ENTER to continue:")

def getBoardCorners():
    """
        Get the robots rotation/stretch locations centered on each corner of the board in this format:
            [{'rotation': ?, 'stretch': ?},         Bottom left
             {'rotation': ?, 'stretch': ?},         Bottom right
             {'rotation': ?, 'stretch': ?},         Top right
             {'rotation': ?, 'stretch': ?}]         Top left

        This function allows the robot to find the corners of the board by looking for the tiny square markers.
        It first finds the bottom right corner, where it looks for 4 squares of similar sizes. Now that it knows
        the approximate size of the squares, it is able to find the rest of the corners with ease, by looking for
        squares of the same shape.
    :param vid:
    :return:
    """

    global streamVideo

    #This defines the area where the robot will look for corners of the board.
    ## It will then find the marker and refine that to an exact location.
    searchPositions = [{'y': -50, 'x': 142, 'height': 150},   #Bottom Right                     #TODO: move these constants somewhere in the main program, or prompt user for them
                       {'y':  98, 'x': 117},   #Bottom Left
                       {'y': 138, 'x': 254},   #Top Left
                       {'y':  -3, 'x': 288}]   #Top Right

    #searchPositions = [{'y':   -20, 'x':   60, 'height': 150},   #TODO: move these constants somewhere in the main program, or prompt user for them
    #                   {'y':   100, 'x': 120},
    #                   {'y':   120, 'x': 240},
    #                   {'y':   -40, 'x': 260}]

    #  FIND AVERAGE AREA OF THE MARKERS BY LOOKING FOR 4 SIMILIAR AREA MARKERS ON THE BOTTOM RIGHT CORNER OF THE BOARD.
    #  THIS AVERAGE AREA VALUE WILL THEN BE USED TO IDENTIFY MARKERS ON EACH CORNER OF THE BOARD.
    #  TODO: Make sure that if it doesn't see 4 small blocks, that it doesn't confuse the big ones as the markers
    Robot.moveTo(relative = False, **searchPositions[0])
    sleep(2)

    tolerance       = vid.frame.shape[0] * vid.frame.shape[1] * 0.001  #Find 4 shapes that are .1% Similar
    avgArea         = 0  #The average pixel area of the markers.
    while avgArea == 0:
        shapeArray = objTracker.getShapes(4, minArea = 500, maxArea = (vid.frame.shape[0] * vid.frame.shape[1]) / 10)[::-1]
        for shapeIndex, shape in enumerate(shapeArray):
            shapeArrayCompare = shapeArray[:shapeIndex] + shapeArray[(shapeIndex + 1):]  #Get shapeArray without the current shape being analyzed
            similarShapes     = [shape]
            for compareIndex, shapeToCompare in enumerate(shapeArrayCompare):
                if shape.area - tolerance < shapeToCompare.area < shape.area + tolerance:
                    similarShapes.append(shapeToCompare)
            if len(similarShapes) == 4:
                avgArea = sum([s.area for i, s in enumerate(similarShapes)]) / len(similarShapes)
                print "getBoardCorners(): Average area of markers found to be: ", avgArea
                break

        if avgArea == 0: #If the 4 markers were never identified
            print "getBoardCorners(): ERROR: First marker not found! Trying again..."

    #  NOW THAT AVG AREA HAS BEEN FOUND, GO TO EACH POSITION, FIND THE MARKER, FOCUS VIEW ON IT, AND RECORD THE ROBOTS POSITION ATOP EACH MARKER
    cornerPositions = []
    #getMarkers     = lambda: objTracker.bruteGetFrame(lambda: objTracker.getShapes(4, minArea = avgArea - tolerance, maxArea = avgArea + tolerance), attempts = 30)
    #markerCenter   = lambda: objTracker.getShapesCentroid(getMarkers())

    for index, position in enumerate(searchPositions):
        Robot.moveTo(relative = False, **position)
        sleep(1.5)

        circles = vid.frame.copy()
        #cv2.circle(circles, tuple(markerCenter()), 25, (0, 0, 255), 3, 255)  #Draw center of circle

        #streamVideo = False
        #vid.windowFrame["Main"] = objTracker.drawShapes(getMarkers(), frameToDraw = circles)
        #sleep(3)
        streamVideo = True

        markerCoordinate = lambda: findMarker(avgArea, tolerance)

        focusOnTarget(markerCoordinate, tolerance = 5)
        cornerPositions.append(Robot.getPosArgsCopy(onlyRecord = ["x", "y"]))  #Record the robots current position

    print "getBoardCorners(): Final Corners: ", cornerPositions
    return cornerPositions

def getAverageColor(circleArray):
    """
    The pieces on the board are determined to be one side or another by their color. Since color can be be read differently
    in different lightings, this function can be used to calibrate at the start of the game.

    What it does is it takes the average color of each circle and returns it. This is then used to find the "midpoint"
    for determining if one piece is from player A or player B. It must only be run when there is an equal number
    of each type of piece on the board, or it will skew the results.
    """
    avgColor = [0, 0, 0]
    for circle in circleArray:
        avgColor = [avgColor[0] + circle.color[0],
                    avgColor[1] + circle.color[1],
                    avgColor[2] +  circle.color[2]]
    avgColor = [avgColor[0] / len(circleArray), avgColor[1] / len(circleArray), avgColor[2] / len(circleArray)]
    print "getAverageColor(): ", avgColor
    return avgColor

def getBoardOverview(cornerLocations, **kwargs):
    """
    Gets several images of the board and stitches them together to return a stitched image of the whole board.
    It then resizes the image if the appropriate kwarg is set.
    """
    finalWidth = kwargs.get("finalImageWidth", -1)
    # picturePositions = [{'x': (cornerLocations[0]["x"] + cornerLocations[1]["x"]) / 2,
    #                      'y': (cornerLocations[0]["y"] + cornerLocations[1]["y"]) / 2},
    #                     {'x': (cornerLocations[2]["x"] + cornerLocations[3]["x"]) / 2,
    #                      'y': (cornerLocations[2]["y"] + cornerLocations[3]["y"]) / 2}]

    picturePositions = [{'x': (cornerLocations[0]["x"] + cornerLocations[1]["x"]) / 2,
                         'y': (cornerLocations[0]["y"] + cornerLocations[1]["y"]) / 2},
                        {'x': (cornerLocations[2]["x"] + cornerLocations[3]["x"]) / 2,
                         'y': (cornerLocations[2]["y"] + cornerLocations[3]["y"]) / 2}]

    boardLength = (picturePositions[1]['x'] - picturePositions[0]['x'])
    picturePositions[0]['x'] = picturePositions[0]["x"] + boardLength / 4
    picturePositions[1]['x'] = picturePositions[1]["x"] - boardLength / 4

    print picturePositions

    #picturePositions = [{'rotation': -13, 'stretch': 107, 'height': 150},  #TODO: Derive this array from info from getBoardCorners()
    #                    {'rotation': -13, 'stretch': 42}]
        #                [{'rotation': -11, 'stretch': 70,  'height': 150},
        #                 {'rotation': -8, 'stretch': 140,  'height': 150},
        #                 {'rotation': -17, 'stretch': 140, 'height': 150},
        #                 {'rotation': -21, 'stretch': 45,  'height': 150},
        #                 {'rotation': -8, 'stretch': 35,   'height': 150}]

    images_array = []
    for index, position in enumerate(picturePositions):
        Robot.moveTo(relative = False, **position)
        sleep(1.5)
        images_array.append(vid.frame)

    final_img = ImageStitching.stitchImages(images_array[0], images_array[1:], 0)


    # RESIZE THE IMAGE IF THE finalWidth FUNCTION AN ARGUMENT
    if not finalWidth == -1:
        resized = vid.resizeFrame(final_img, finalWidth)
        return resized

    return final_img

def getBoardState(frame, circleArray, screenDimensions, redThreshold):
    boardSize = 6
    board = [[0 for i in range(boardSize)] for j in range(boardSize)]
    squareSize = (screenDimensions[0] / boardSize)
    dist       = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5  #sign(x) will return the sign of a number'


    frameToDraw = frame.copy()

    for column in range(boardSize):
        for row in range(boardSize):
           # print "row: ", row, "column: ", column, "squareSize: ", squareSize
            location = [squareSize * row + squareSize / 2, squareSize * column + squareSize / 2]
           # print location
            if len(circleArray) == 0: continue

            circleArray = sorted(circleArray, key = lambda c: (c.center[0] - location[0]) ** 2 + (c.center[1] - location[1]) ** 2)
            nearest     = circleArray[0]


            if dist(nearest.center, location) < squareSize / 2:
                fromX = int(nearest.center[0] - nearest.radius / 2)
                toX   = int(nearest.center[0] + nearest.radius / 2)
                fromY = int(nearest.center[1] - nearest.radius / 2)
                toY   = int(nearest.center[1] + nearest.radius / 2)

                if nearest.color[2] > redThreshold:
                    board[column][row] = 1  #IF IS RED PIECE
                    color = (0, 0, 255)
                else:
                    board[column][row] = 2  #IF IS GREEN PIECE
                    color = (0, 255, 0)

                cv2.rectangle(frameToDraw, tuple([fromX, fromY]), tuple([toX, toY]), color, 3)
                cv2.putText(frameToDraw, str(row) + "," + str(column), (nearest.center[0] - 25, nearest.center[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 1, 0)
                del circleArray[0]
        #print board[column]
    return board, frameToDraw

def getSquarePosition(row, column, corners):
    """
    This function returns the estimated robot rotation/stretch that a board square is located in.
    It does this by using the cornerLocations information to estimate the location of a square on the board.
    May not always work accurately, but should speed things up.

    This function will return a coordinate in this format: {"x": ?, "y": ?}
    This format can be sent to Robot.moveTo() command easily.

    Row and column: Where on the board you wish the camera to jump to
    :param corners: The array gotten from getBoardCorners()
    """

    boardSize = float(6)

    #For simplicity, get the bottom Right (bR) bottom Left (bL) and so on for each corner.
    dist   = lambda p1, p2: ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** .5
    ptDist = lambda d, a, b: [a[0] + ((b[0] - a[0]) / dist(a, b)) * d, a[1] + ((b[1] - a[1]) / dist(a, b)) * d]

    #GET [x,y] FORMAT COORDINATES FOR EACH CORNER OF THE CHECKERBOARD
    bR = [float(corners[0]["x"]), float(corners[0]["y"])]
    bL = [float(corners[1]["x"]), float(corners[1]["y"])]
    tR = [float(corners[3]["x"]), float(corners[3]["y"])]
    tL = [float(corners[2]["x"]), float(corners[2]["y"])]

    #GET LENGTH OF EACH SIDE
    lenBot = dist(bR, bL)
    lenTop = dist(tR, tL)
    lenRit = dist(bR, tR)
    lenLef = dist(bL, tL)


    #GET POINTS ON EACH SIDE THAT ARE CLOSEST TO THE DESIRED SPOT. ADD .5 TO ROW AND COLUMN CENTER VIEW ON THE MIDDLE OF THE SQUARE
    ptTop = ptDist((lenTop / boardSize) * (column + .5), tL, tR)
    ptBot = ptDist((lenBot / boardSize) * (column + .5), bL, bR)
    ptLef = ptDist((lenLef / boardSize) * (row + .5),    tL, bL)
    ptRit = ptDist((lenRit / boardSize) * (row + .5),    tR, bR)


    #GET THE POINT OF INTERSECTION, WHICH WILL BE THE FINAL POINT FOR THE ROBOT TO GO TO
    s1_x = ptBot[0] - ptTop[0]
    s1_y = ptBot[1] - ptTop[1]
    s2_x = ptRit[0] - ptLef[0]
    s2_y = ptRit[1] - ptLef[1]
    t = (s2_x * (ptTop[1] - ptLef[1]) - s2_y * (ptTop[0] - ptLef[0])) / (-s2_x * s1_y + s1_x * s2_y)
    #cornerOfSquare = [ptTop[0] + (t * s1_x), ptTop[1] + (t * s1_y)]

    finalCoords = {'x': ptTop[0] + (t * s1_x), 'y': ptTop[1] + (t * s1_y)}

    print "getSquarePosition(): bottomL: ", lenBot, " topL: ", lenTop, " rightL: ", lenRit, " leftL: ", lenLef
    print "getSquarePosition(): topPoint: ", ptTop, " botPoint: ", ptBot, " lefPoint: ", ptLef, " ritPoint: ", ptRit
    print "getSquarePosition(): topLeft: ", tL, " topRight: ", tR, " bottomRight: ", bR, " bottomLeft: ", bL

    print "getSquarePosition(): FinalCoords: ", finalCoords
    return finalCoords
    
def findMarker(avgArea, tolerance, **kwargs):


    maxAttempts = kwargs.get("maxAttempts", 50)
    squaresInMarker = 4  #The camera must detect exactly 4 squares of the same size to consider it to be a marker
    attempts = 0

    shapes = []
    while not len(shapes) >= 4 and attempts <= maxAttempts:

        shapes = objTracker.getShapes(4, minArea = avgArea - tolerance, maxArea = avgArea + tolerance)
        attempts += 1

        #IF NOT SUCCESSFULL, PULL ANOTHER FRAME
        if len(shapes) < squaresInMarker:

            if attempts != maxAttempts:
                lastFrame = vid.frameCount
                while lastFrame == vid.frameCount:
                    pass
            else:
                print "findMarker:() ERROR: ATTEMPTS OVER ", maxAttempts
                raise NameError("ObjNotFound")

    #Shorten the list to the squares closest to center screen (Most likely to be relevant markers)
    shapes = objTracker.sortShapesByDistance(shapes)[:4]

    markerCentroid = tuple(objTracker.getShapesCentroid(shapes))

    if len(markerCentroid) == 0:
        print "findMarker:(): ERROR: No marker centroid detected"
        raise NameError("ObjNotFound")

    return markerCentroid

#MAIN THREADS
def runRobot():
    #SET UP VARIABLES AND RESET ROBOT POSITION
    print 'runRobot(', locals().get('args'), '): Setting up Robot Thread....'
    #global exitApp
    global keyPressed  #Is set in the main function, because CV2 can only read keypresses in the main function. Is a character.

    Robot.moveTo(relative = False, waitForRobot = True, **Robot.home)
    Robot.setGrabber(0)

    playCheckers()

    #MAIN ROBOT FUNCTION
    # while not exitApp:
    #
    #     if keyPressed == 'h':  #HELP COMMAND
    #         print 'Help: \n x: MOVETOXY'
    #
    #
    #     if keyPressed == 'x':  #MOVE TO XY
    #         #Robot.moveTo(height = float(raw_input('Height?:')), rotation = float(raw_input('Rotation?:')), stretch = float(raw_input('Stretch:')), relative = False)
    #         #Robot.moveTo(height = 150, rotation = float(raw_input('Rotation?:')), stretch = float(raw_input('Stretch:')), relative = False)
    #         #Robot.moveTo(height = 150, stretch = float(raw_input('Stretch:')), relative = False)
    #         Robot.moveTo(x=float(raw_input('X?: ')), y=float(raw_input('Y?: ')), relative=False)
    #
    #     if keyPressed == 'p':  #PLAY CHECKERS
    #         playCheckers()

if '__main__' == __name__:
    print 'Start!'
    #SET UP VIDEO CLASS AND WINDOWS VARIABLES
    vid                 = Vision.Video()
    vid.createNewWindow('Main',             xPos = 20,  yPos = 10)
    vid.createNewWindow('Perspective',      xPos = 120,  yPos = 10)
    vid.setCamResolution(1000, 1000)  #Sets the resolution as high as the camera allows
    vid.getVideo(readXFrames= 6)   #Get the first few frames


    #SETUP UP OTHER VARIABLES/CLASSES
    objTracker          = Vision.ObjectTracker(vid, rectSelectorWindow = 'KeyPoints')
    screenDimensions    = vid.getDimensions()
    keyPressed          = ''  #Keeps track of the latest key pressed


    global exitApp
    global streamVideo       #RobotThread communicates using this. It tells main thread to stream video onto window or to hold on a particular frame.
    exitApp         = False
    streamVideo     = True  #If true, then the camera will stream video. If not, then the camera will wait for new frames to be called for from the runCheckers() thread


    #START SEPERATE THREAD FOR MOVING ROBOT
    robotThread = Thread(target = runRobot)
    robotThread.start()


    #DISPLAY VIDEO/IMAGE REC. MAIN THREAD.
    while not exitApp:
        vid.getVideo()


        #DETECT IF CAMERA HAS BEEN UNPLUGGED, AND IF SO TRY TO RECONNECT EVERYTHING:
        #if objTracker.getMovement() == 0:
        #    print 'ERROR: __main__(XXX): Camera NOT detected.'
        #    sleep(1)
        #    print '__main(XXX)__: Attempting to reconnect...'
        #    vid.cap = cv2.VideoCapture(1)

        if streamVideo:
            # avgArea = 1040
            # tolerance       = vid.frame.shape[0] * vid.frame.shape[1] * 0.001  #Find 4 shapes that are .1% Similar
            # try:
            #    marker = findMarker(avgArea, tolerance, maxAttempts = 1)
            # except NameError as e:
            #    #print "__Main__(): ERROR: ", e, ": No marker found"
            #    marker = (0, 0)


            #CIRCLE THE NEAREST CIRCLE
            markedUpFrame = vid.frame.copy()
            #cv2.circle(markedUpFrame, marker, 6, (0, 0, 2550), 3, 255)  #Draw Circle on Marker
            cv2.circle(markedUpFrame, (int(screenDimensions[0] / 2), int(screenDimensions[1] / 2)), 6, (0, 255, 0), 3, 255)  #Draw center of circle
            circles = objTracker.getCircles(frameToAnalyze = markedUpFrame, minRadius =25)  #Get circles on screen
            if len(circles) > 0:
                nearestCircle = [objTracker.sortShapesByDistance(circles)[0]]
                markedUpFrame = objTracker.drawCircles(nearestCircle, frameToDraw = markedUpFrame)

            vid.windowFrame["Main"] = markedUpFrame

            #vid.windowFrame["Main"] = vid.frame




        #DISPLAY WHATEVER FRAME IS NEXT
        vid.display('Main')
        vid.display('Perspective')

        #RECORD KEYPRESSES AS A CHARACTER IN A STRING
        ch = cv2.waitKey(1)                                    #Wait between frames, and also check for keys pressed.
        keyPressed = chr(ch + (ch == -1) * 256).lower().strip()  #Convert ascii to character, and the (ch == -1)*256 is to fix a bug. Used mostly in runRobot() function
        if keyPressed == chr(27): exitApp = True                 #If escape has been pressed, close program
        if keyPressed == 'p':                                    #Pause and unpause when spacebar has been pressed
            vid.paused = not vid.paused
            print '__main(XXX)__: PAUSED: ', vid.paused


    #CLOSE EVERYTHING CORRECTLY
    robotThread.join(1)  #Ends the robot thread, waits 1 second to do so.
    Robot.setGrabber(1)
    cv2.destroyWindow('window')


print 'End!'