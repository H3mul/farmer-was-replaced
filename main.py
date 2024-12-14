
def prepareSoil(grass):
    if grass:
        targetSoil = Grounds.Turf
    else:
        targetSoil = Grounds.Soil
    if get_ground_type() != targetSoil:
        till()

def ensureItem(item, logFailure = True):
    if num_items(item) == 0:
        success = trade(item, farmConfig["buyCount"])
        if not success and logFailure:
            quick_print("Failure: can't get enough of", item)
        return success
    return True

def autoPlant(entity):
    prepareSoil(entity == Entities.Grass or entity == Entities.Bush)

    success = True
    if entity == Entities.Carrots:
        success = ensureItem(Items.Carrot_Seed)
    elif entity == Entities.Pumpkin:
        success = ensureItem(Items.Pumpkin_Seed)
    elif entity == Entities.Cactus:
        success = ensureItem(Items.Cactus_Seed)
    elif entity == Entities.Sunflower:
        success = ensureItem(Items.Sunflower_Seed)

    if not success:
        return False

    plant(entity)
    return True

def autoPlantWithFailure(entity):
    if not autoPlant(entity):
        farmConfig["rotation"]["rotationFailed"] = True
        return False
    return True

def getLargestSunflower():
    if len(farmConfig["sunflowers"]["largestStack"]) == 0:
        return None
    largestM = farmConfig["sunflowers"]["largestStack"][-1]
    if largestM not in farmConfig["sunflowers"]["largestCoords"]:
        return None
    largestCoords = farmConfig["sunflowers"]["largestCoords"][largestM]

    return (largestM, largestCoords)

def bisortInsert(list, value, start, end):
    if end - start <= 1:
        list.insert(start + 1, value)
        return

    mid = (start + end) // 2
    if list[mid] > value:
        bisortInsert(list, value, start, mid)
    else:
        bisortInsert(list, value, mid, end)

def insertUniqueSorted(list, value):
    if value not in list:
        bisortInsert(list, value, 0, len(list))

def addSunflower(x = get_pos_x(), y = get_pos_y()):
    if get_entity_type() != Entities.Sunflower:
        return

    m = measure()

    if m not in farmConfig["sunflowers"]["largestCoords"]:
        farmConfig["sunflowers"]["largestCoords"][m] = {(x,y)}
    else:
        farmConfig["sunflowers"]["largestCoords"][m].add((x,y))

    insertUniqueSorted(farmConfig["sunflowers"]["largestStack"], m)

def harvestSunflower(x = get_pos_x(), y = get_pos_y()):
    coords = (x,y)
    sunflower = getLargestSunflower()

    if sunflower == None:
        return False

    largestM, largestCoords = sunflower
    if coords in largestCoords:
        largestCoords.remove(coords)
        if len(largestCoords) == 0:
            farmConfig["sunflowers"]["largestStack"].pop()
            farmConfig["sunflowers"]["largestCoords"].pop(largestM)

        if largestM == measure():
            return True
    return False

def autoWater():
    if num_items(Items.Water_Tank) > 0 and get_water() <= 0.05:
        use_item(Items.Water_Tank)

def fertilizeToFull(logFailure = False):
    while not can_harvest():
        if not autoFertilize(logFailure):
            return False

def autoFertilize(logFailure = False):
    itemAvailable = ensureItem(Items.Fertilizer, logFailure)
    if not itemAvailable:
        return False
    return use_item(Items.Fertilizer)

def planCompanion():
    companion = get_companion()
    if companion == None:
        return

    target, x, y = companion
    farmConfig["fieldMatrix"][x][y] = target


def shouldHarvest(crop, x, y):
    if crop == Entities.Pumpkin:
        return not farmConfig["fieldMatrix"][x][y] == Entities.Pumpkin or farmConfig["pumpkinHarvestPointMatrix"][x][y]
    else:
        return True

def farmTile(x = get_pos_x(), y = get_pos_y()):
    if not can_harvest() and farmConfig["useFertilizer"]:
        fertilizeToFull(False)

    if can_harvest() and shouldHarvest(get_entity_type(), x, y):
        harvest()

    crop = farmConfig["fieldMatrix"][x][y]
    if crop == None:
        crop = planFarmTile(x, y)

    if not autoPlantWithFailure(crop):
        quick_print("Failed to plant crop, failing rotation")
        return False
    if farmConfig["plantCompanions"] and getCurrentRotation() == "farm":
        planCompanion()

    addSunflower(x, y)
    autoWater()
    return True

def getCropFactor(entity):
    if entity not in farmConfig["cropWeights"]:
        return 0
    return farmConfig["cropWeights"][entity] / farmConfig["totalCropWeight"]

def planFarmTile(x = get_pos_x(), y = get_pos_y()):
    for crop in farmConfig["rotation"]["rotationToEntity"]["farm"]:
        if crop == Entities.Tree:
            if (x % 2 + y % 2) % 2 and random() < getCropFactor(Entities.Tree) * 2:
                return Entities.Tree

        if random() < getCropFactor(crop):
            return crop

    return Entities.Grass

def moveTo(x, y):
    # TODO optimize using world wrapping
    for i in range((get_pos_x() - x) % farmConfig["fieldSize"]):
        move(West)
    for i in range((get_pos_y() - y) % farmConfig["fieldSize"]):
        move(South)

def buyWater():
    n = farmConfig["waterTanks"]
    buyWaterTanks = n - (num_items(Items.Water_Tank) + num_items(Items.Empty_Tank))
    if buyWaterTanks > 0:
        trade(Items.Empty_Tank, buyWaterTanks)

def scanField(action, marginX = 0, marginY = 0):
    limitX = farmConfig["fieldSize"] - 2 * marginX
    limitY = farmConfig["fieldSize"] - 2 * marginY
    moveTo(marginX, marginY)

    if get_pos_x() <= marginX:
        horizontalMove = East
    else:
        horizontalMove = West

    for i in range(limitX):
        if get_pos_y() <= marginY:
            verticalMove = North
        else:
            verticalMove = South

        for j in range(limitY):
            if not action():
                return False

            if j < limitY - 1:
                move(verticalMove)
        move(horizontalMove)

    return True

def prepareMaze():
    if get_entity_type() == Entities.Hedge:
        return

    if get_entity_type() != Entities.Bush:
        harvest()
    if get_ground_type() != Grounds.Turf:
        till()

    autoPlant(Entities.Bush)

    while get_entity_type() == Entities.Bush:
        if not autoFertilize():
            return False
    return True

def negateDir(n):
    inverseDir = { North: South, East: West, South: North, West: East}
    if n in inverseDir:
        return inverseDir[n]
    else:
        return None

def bruteForceMaze(fromDir = None):
    for dir in [North, East, West, South]:
        if fromDir == dir:
            continue

        if get_entity_type() == Entities.Treasure:
            harvest()
            return True

        if not move(dir):
            continue

        if bruteForceMaze(negateDir(dir)):
            return True

    if (fromDir):
        move(fromDir)
    return False

def fillMatrix(matrix, size = None, value = None, x = 0, y = 0):
    if not size:
        size = len(matrix)

    for i in range(x, x + size):
        for j in range(y, y + size):
            matrix[i][j] = value

def blankFieldMatrix(value = None):
    field = []

    for i in range(farmConfig["fieldSize"]):
        row = []
        for j in range(farmConfig["fieldSize"]):
            row.append(value)

        field.append(row)
    return field

def prepareFieldWithCrop(entity):
    clearField()
    farmConfig["fieldMatrix"] = blankFieldMatrix(entity)
    if not scanField(farmTile):
        quick_print("prepareFieldWithCrop failed")
        farmConfig["rotation"]["rotationFailed"] = True

def cactusSwap(dir):
    swap(dir)
    farmConfig["cactus"]["swapsThisEpoch"] += 1

def sortCactusTile(x = get_pos_x(), y = get_pos_y()):
    if get_entity_type() != Entities.Cactus:
        quick_print("Can't sort cactus: no cactus in this tile")
        return False

    m = measure()

    for i in range(2):
        if y > 0 and measure(South) > m:
            cactusSwap(South)
        if y < farmConfig["fieldSize"] - 1 and measure(North) < m:
            cactusSwap(North)
        if x > 0 and measure(West) > m:
            cactusSwap(West)
        if x < farmConfig["fieldSize"] - 1 and measure(East) < m:
            cactusSwap(East)
    return True

def farmCactus(x = get_pos_x(), y = get_pos_y()):
    farmConfig["cactus"]["swapsThisEpoch"] = 0

    if not scanField(sortCactusTile):
        quick_print("Cactus sort scan failed, failing rotation")
        farmConfig["rotation"]["rotationFailed"] = True
        return False

    swapFactor = farmConfig["cactus"]["swapsThisEpoch"] / (4*farmConfig["fieldSize"]*farmConfig["fieldSize"])

    if  swapFactor <= farmConfig["cactus"]["swapFactorForHarvest"]:
        fertilizeToFull()
        harvest()
        return True
    return False

def farmSunflowers():
    _, largestCoords = getLargestSunflower()

    for coord in largestCoords:
        x, y = coord

        moveTo(x, y)

        fertilizeToFull()

        if get_entity_type() != Entities.Sunflower or harvestSunflower(x, y):
            harvest()

        autoPlant(Entities.Sunflower)
        autoWater()
        addSunflower(x, y)
        break

def planPumpkins():
    clearFieldMatrix()
    farmConfig["pumpkinHarvestPointMatrix"] = blankFieldMatrix()

    patchCountMax = 1 + (farmConfig["fieldSize"] - 4) // 5

    for i in range(patchCountMax):
        for j in range(patchCountMax):
            fillMatrix(farmConfig["fieldMatrix"], 4, Entities.Pumpkin, i * 5, j * 5)
            farmConfig["pumpkinHarvestPointMatrix"][i * 5][j * 5] = True

def clearField():
    scanField(harvest)

def printMatrix(matrix):
    quick_print("[")
    for i in matrix:
        quick_print(i)
    quick_print("]")

def getCurrentRotation():
    return farmConfig["rotation"]["rotations"][farmConfig["rotation"]["currentIdx"]]

def shiftRotation():
    farmConfig["rotation"]["currentIdx"] = (farmConfig["rotation"]["currentIdx"] + 1) % len(farmConfig["rotation"]["rotations"])
    return getCurrentRotation()

def incrementEpoch():
    farmConfig["epoch"] = (farmConfig["epoch"] + 1)
    if len(farmConfig["rotation"]["rotations"]) > 1:
        rotationEpochs = farmConfig["rotation"]["rotationEpochs"] * farmConfig["rotation"]["rotationEpochMultipliers"][getCurrentRotation()]
        farmConfig["epoch"] = farmConfig["epoch"] % rotationEpochs

def clearFieldMatrix():
    farmConfig["fieldMatrix"] = blankFieldMatrix()

def init():
    farmConfig["fieldSize"] = get_world_size()
    clearFieldMatrix()

    farmConfig["buyCount"] = farmConfig["fieldSize"]*farmConfig["fieldSize"]

    farmConfig["totalCropWeight"] = 0
    for e in farmConfig["rotation"]["rotationToEntity"]["farm"]:
        farmConfig["totalCropWeight"] += farmConfig["cropWeights"][e]
    
    for rotation in farmConfig["rotation"]["rotationToEntity"]:
        exclude = True
        for e in farmConfig["rotation"]["rotationToEntity"][rotation]:
            if getCropFactor(e) > 0:
                exclude = False
        if exclude:
            farmConfig["rotation"]["rotations"].remove(rotation)


# =======================================

farmConfig = {
    "buyCount": 0,
    "waterTanks": 1000,
    "plantCompanions": True,
    "useFertilizer": True,
    "cropWeights": {
        Entities.Grass: 0,
        Entities.Bush: 0,
        Entities.Tree: 0,
        Entities.Carrots: 0,
        Entities.Pumpkin: 1,
        Entities.Treasure: 1,
        Entities.Sunflower: 0,
        Entities.Cactus: 0,
    },
    "totalCropWeight": 0,
    "cactus": {
        "swapFactorForHarvest": 0.3,
        "swapsThisEpoch": 0
    },
    "sunflowers": {
        "largestStack": [-1],
        "largestCoords": {-1: {(-1,-1)}}
    },
    "pumpkinHarvestPointMatrix": [[]],
    "fieldMatrix": [[]],
    "fieldSize": 0,
    "cactusSortingComplete": False,
    "epoch": 0,
    "rotation": {
        "rotationFailed": False,
        "rotationToEntity": {
            "farm": [Entities.Bush, Entities.Carrots, Entities.Grass, Entities.Tree],
            "treasure": [Entities.Treasure],
            "sunflowers": [Entities.Sunflower],
            "pumpkins": [Entities.Pumpkin],
            "cactus": [Entities.Cactus],
        },
        "rotationEpochMultipliers": {
            "farm": 1,
            "pumpkins": 1,
            "cactus": 100,
            "treasure": 3,
            "sunflowers": 10,
        },
        "rotations": [ "cactus", "treasure", "pumpkins", "farm", "sunflowers" ],
        "rotationEpochs": 10,
        "currentIdx": -1
    }
}

init()

quick_print("Active rotations:", farmConfig["rotation"]["rotations"])

buyWater()
moveTo(0,0)

while True:
    if farmConfig["fieldSize"] != get_world_size():
        init()

    firstRotationEpoch = farmConfig["epoch"] == 0

    if farmConfig["rotation"]["rotationFailed"]:
        quick_print("Detected failed rotation, shifting to next")

    if firstRotationEpoch or farmConfig["rotation"]["rotationFailed"]:
        shiftRotation()
        farmConfig["rotation"]["rotationFailed"] = False
        quick_print("Starting rotation: ", getCurrentRotation())

    if getCurrentRotation() == "farm":
        if firstRotationEpoch:
            clearFieldMatrix()
        scanField(farmTile)
    elif getCurrentRotation() == "sunflowers":
        if firstRotationEpoch:
            prepareFieldWithCrop(Entities.Sunflower)
        farmSunflowers()
    elif getCurrentRotation() == "pumpkins":
        if firstRotationEpoch:
            planPumpkins()
        scanField(farmTile)
    elif getCurrentRotation() == "cactus":
        if firstRotationEpoch or farmCactus():
            prepareFieldWithCrop(Entities.Cactus)
    elif getCurrentRotation() == "treasure":
        prepareMaze()
        bruteForceMaze()

    incrementEpoch()