import psycopg2
import numpy
from spellchecker import SpellChecker # TODO ADD SHIT
import pandas as pd # REMEMBER TO CHECK
import pandas.io.sql as sqlio # REMEMBER TO CHECK
import datetime
import random
import math

##### LEGACY #####

# These functions were used in previous versions,
# and as of right now are unused; they could however
# be useful in the future.

def filter_unmatched_stint(stint):
    """
    Checks which stints have been assigned ('matched') and which ones are still waiting for a student ('unmatched').
    
    In:
        stint (pandas.DataFrame) = Panda object of stints
    Out (tuple):
        stint_unmatched (list) = List of unmatched stint id's
        stint_matched (list) = List of matched stint id's
    """
    stint_matched, stint_unmatched = [], []
    for (st_id,student_id) in zip(stint.get('id'),stint.get('student_id')):
        if numpy.isnan(student_id):
            stint_unmatched.append(st_id)
        else:
            stint_matched.append(st_id)
    return (stint_unmatched,stint_matched)

def fast_track(conn, no_stint_business,  student_available, business_id, stint_id):
    """
    Chooses students to 'fast track' for a business following three different criteria.
    In:
        conn (connection) = Connection to SQL 
        no_stint_business (int) = Number of stints done by the business
        student_available (list) = List of id's of available students for this stint
        business_id (int) = id of business
        stint_id (int) = id of stint
    Out:
        n/a
    Global changes:
        final_list (list) = Appends student id's to final list
    """

    if no_stints_business(conn, business_id ) < 4: ### CHECK IF BUSINESS IS BEGINNER
        pass ### ASSIGN BEST STUDENTS
        return
    
    for student_id in student_available: ### CHECK IF STUDENT(S) HAS(HAVE) WORKED WITH BUSINESS BEFORE
        stint_connection = stint_student_business(conn, business_id, student_id)
        if stint_connection["worked_together"]:
            grade_list = []
            for stint_id in stint_connection["stint_id_list"]:
                cursor = conn.cursor()
                sql_command = "SELECT grade FROM storm_review WHERE stint_id='{}' AND grade IS NOT NULL;".format(stint_id)
                cursor.execute(sql_command)
                grade_list.append(cursor[0])
            if grade_list == []:
                break
            else:
                if numpy.mean(grade_list) > average_business_rating(conn, business_id)['mean_grade']:  
                    final_list.append(stint_connection["student_id"])
                    
    ### PSEUDO CODE BELOW !!! ###

    if business_level == "medium": ### CHECK IF BUSINESS LEVEL IS MEDIUM
        chosen_students = []
        for i in range(len(student_available)):
            try:
                random_student_id = random.choice(set(student_available).difference(set(chosen_students)))
            except:
                continue
            if random_student_id not in chosen_students:
                chosen_students.append(random_student_id)
                if no_stints_student(conn, random_student_id) < 3:
                    final_list.append(random_student_id)
                    break

    ### PSEUDO CODE ABOVE !!! ###    

##### FILTERS #####

def filter_available_students(conn, stint_id):
    """
    Checks students available for a specific stint (time-wise)
    In:
        conn (connection) = Connection to SQL
        stint_id (string) = id of stint
    Out:
        students_available (dict) = dict containing student and availability id's (for a stint) 
    """
    suitable_students = filter_suitable(conn) # Invoke filter_suitable() to fetch all students able to work.
    students_available = []
    sql_command = "SELECT date_from, date_to FROM storm_stint WHERE id='{}';".format(stint_id)
    cursor_date_stint = conn.cursor()
    cursor_date_stint.execute(sql_command)

    for object_time in cursor_date_stint: 
        date_from_stint = object_time[0]
        date_to_stint = object_time[1]

    for student_id in suitable_students:
        sql_command_student = "SELECT date_from, date_to, id FROM storm_studentavailability WHERE student_id='{}';".format(student_id)
        cursor_date_student = conn.cursor()
        cursor_date_student.execute(sql_command_student)
        for object_time in cursor_date_student:
            date_from_student = object_time[0]
            date_to_student = object_time[1]
            student_av_id = object_time[2]
            if date_from_student <= date_from_stint and date_to_student >= date_from_stint: # Filter out the students whose availability does not coincide
                students_available.append({'student_id':student_id,'student_av_id':student_av_id})

    return students_available

def filter_suitable(conn):
    """
    Filters out 'disabled', non verified and suspended students.
    In:
        conn (connection) = Connection to SQL
    Out:
        suitable_students (list) = List of non disabled, verified and non suspended student id's
    """  
    suitable_students = []
    
    sql_command = "SELECT baseuser_ptr_id FROM storm_student WHERE is_verified='t' AND is_suspended='f' AND is_on_waiting_list='f';"   
    cursor = conn.cursor()
    cursor.execute(sql_command)

    for base_id in cursor:
        sql_command = "SELECT is_disabled FROM storm_baseuser WHERE id='{}';".format(base_id[0])
        cursor_dis = conn.cursor()
        cursor_dis.execute(sql_command)
        for bool_disabled in cursor_dis:
            if bool_disabled[0] is False:
                suitable_students.append(base_id[0])

    return suitable_students  

##### EXPERIENCE #####

# Students Experience #

def no_stints_student(conn,student_id):
    """
    Counts number of stints done by a single student.
    In:
        conn (connection) = Connection to SQL
        student_id (int) = id of student
    Out:    
        no_stints_student (dict) = Number of stints done by a student.
    """
    sql_command = "SELECT id FROM storm_stint WHERE student_id='{}';".format(student_id)
    cursor = conn.cursor()
    cursor.execute(sql_command)
    no_stints_student = {'student_id':student_id,'number_of_stints':cursor.rowcount}
    
    return no_stints_student

def same_type_stint_student(conn, student_id, stint_type):
    """
    Outputs a dict of lists of stints of the same type made by ONE student.
    In: 
        conn (connection) = Connection to SQL
        student_id (int) = id of student
        stint_type (string) = type of stint
    Out:
        same_type_stint_student (dict) = Dict representing types of stints (and a list of id's) done by a student
    """    
    cursor_rev = conn.cursor()
    sql_command = "SELECT id, type FROM storm_stint WHERE student_id = '{}';".format(student_id)
    cursor_rev.execute(sql_command)
    stint_id_list = []
    for object_cursor in cursor_rev:
        if object_cursor[1]==stint_type:            
            stint_id_list.append(object_cursor[0])
    
    stints_student_and_types = {'student_id':student_id, 'stint_type':stint_type,'stint_id_list':stint_id_list}
    
    return stints_student_and_types

def stint_student_business(conn, business_id, student_id):
    """
    This function will count how many times a said user has done a stint in a given business.
    In: 
        conn (connection) = Connection to SQL
        business_id (int) = id of business
        student_id (int) = id of stint
    Out: 
        no_stints_business_student (int) = Number of stints done
    """
    cursor = conn.cursor()
    sql_command = "SELECT id FROM storm_stint WHERE business_id='{}' AND student_id='{}';".format(business_id, student_id)
    cursor.execute(sql_command)
    worked_together = False
    
    for obj in cursor:
        if obj[0] != None:
            worked_together = True
    
    stint_id_list = []
    for stint_id in cursor:
        stint_id_list.append(stint_id)
    
    stint_business_student = {'business_id':business_id,'student_id': student_id,'worked_together': worked_together ,'stint_id_list': stint_id_list}
    return stint_business_student

# Business Experience #

def no_stints_business(conn, business_id):
    """
    This function will count how many stints one business has done.
    In: 
        conn (connection) = Connection to SQL
        business_id (int) = id of business
    Out:
        no_stints_business (dict) = Number of stints done by one business in dict form
    """
    sql_command = "SELECT id FROM storm_stint WHERE business_id='{}' AND student_id IS NOT NULL;".format(business_id)
    cursor = conn.cursor()
    cursor.execute(sql_command)
    no_stints_business = {'business_id':business_id,'number_of_stints':cursor.rowcount}
    return no_stints_business

def same_type_stint_business(conn, business_id, stint_type):
    """
    Outputs a list of lists of stints of the same type made by ONE business.
    In:
        conn (connection) = Connection to SQL
        business_id (int) = id of business
        stint_type (string) = type of stint
    Out:
        same_type_stint_business
    """    
    cursor_rev = conn.cursor()
    sql_command = "SELECT id, type FROM storm_stint WHERE business_id = '{}' AND student_id IS NOT NULL;".format(business_id)
    cursor_rev.execute(sql_command)
    stint_id_list = []
    for object_cursor in cursor_rev:
        if object_cursor[1] == stint_type: ## ADD SPELLCHECK IN FUTURE ##
            stint_id_list.append(object_cursor[0])
            
    stints_business_and_types = {'business_id':business_id, 'stint_type':stint_type,'stint_id_list':stint_id_list} # Fill stint_id w/ ids of the same type.
    return stints_business_and_types

#### GRADES #####

# Business Grades #

def average_business_rating(conn, business_id):
    """
    This function will calculate the average of the grading given by a business.
    In:
        conn (connection) = Connection to SQL
        business_id = id of the businessù
    Out:    
    """
    cursor_business = conn.cursor()
    sql_fetch_business = "SELECT grade FROM storm_review WHERE business_id='{}';".format(business_id)
    cursor_business.execute(sql_fetch_business)
    grade_business_list = []
    for grade in cursor_business:
        grade_business_list.append(grade[0])
    
    average_business_rating = {'business_id':business_id ,'mean_grade':numpy.mean(grade_business_list)}
    return (average_business_rating)

def average_business_type_rating(conn, business_id, stint_type): 
    """ 
    Calculates averarage grades given BY a business to a specific type of stint.
    In:
        conn (connection) = Connection to SQL
        business_id (int) = id of business
        stint_type (string) = type of stints
    Out:
        average_business_type (list) = List of average grades given by a business to a type (dicts).
    """
    same_type_stint_business_var = same_type_stint_business(conn, business_id, stint_type)
    list_grades = []
    for stint_id in same_type_stint_business_var['stint_id_list']:
        sql_command = "SELECT grade FROM storm_review WHERE stint_id='{}' AND grade IS NOT NULL;".format(stint_id)
        cursor = conn.cursor()
        cursor.execute(sql_command)
        for cursor_object in cursor:
            list_grades.append(cursor_object[0])
    average_grade_business_type = {'business_id':business_id,'business_type':stint_type,'average_business_type': numpy.mean(list_grades)}

    return average_grade_business_type

# Student Grades #

def delta_grade_student(conn, student_id): 
    """
    Calculate the mean delta of grades of a student.
    In: 
        conn (connection) = Connection with SQL
        student_id (int) = id of student
        stint_type (string) = type of stint
    Out: 
        mean_delta (dict) = Average of deltas of grades of a student in a stint type
    """
    cursor_student = conn.cursor()
    sql_command = "SELECT grade, business_id FROM storm_review WHERE student_id = '{}';".format(student_id)
    cursor_student.execute(sql_command)
    grade_student_list = []
    for cursor_object in cursor_student:
        grade = cursor_object[0] - average_business_rating(conn, cursor_object[1])['mean_grade']
        grade_student_list.append(grade)
    student_grade = {'student_id':student_id,'student_grade':numpy.mean(grade_student_list)}
    return student_grade

def delta_grade_student_type(conn, student_id, stint_type): 
    """
    Calculate the mean delta of grades of a student in a specific stint type.
    In: 
        conn (connection) = Connection with SQL
        student_id (int) = id of student
        stint_type (string) = type of stint
    Out: 
        mean_delta (dict) = Average of deltas of grades of a student in a stint type
    """
    cursor_student_grade = conn.cursor()
    sql_command = "SELECT stint_id, grade FROM storm_review WHERE student_id='{}' AND grade IS NOT NULL;".format(student_id)
    cursor_student_grade.execute(sql_command)
    grades_list = []
    for cursor_element in cursor_student_grade:
        cursor_business = conn.cursor()
        sql_command = "SELECT business_id FROM storm_stint WHERE id='{}' AND type='{}';".format(cursor_element[0], stint_type)
        cursor_business.execute(sql_command)
        for cursor_element_2 in cursor_business:
            delta = cursor_element[1] - average_business_type_rating(conn, cursor_element_2[0], stint_type)['average_business_type']
            grades_list.append(delta)

    mean_delta = {'student_id': student_id, 'stint_type':stint_type, 'mean_delta':numpy.mean(grades_list)}
    return mean_delta

##### DISTANCE and DURATION #####

def distance(conn,stint_id,student_av_id):
    """
    Calculates distance between a student, at a specific availability, and a stint
    In:
        conn (connection) = Connection to SQL
        stint_id (int) = id of stint
        student_av_id (int) = id of student availability slot
    Out:
        distance (int) = Distance between student and stint (in km)
    """
    sql_command = "SELECT longitude, latitude FROM storm_stint WHERE id='{}';".format(stint_id)
    cursor_stint = conn.cursor()
    cursor_stint.execute(sql_command)
    
    sql_command_student = "SELECT longitude, latitude FROM storm_studentavailability WHERE id='{}';".format(student_av_id)
    cursor_av = conn.cursor()
    cursor_av.execute(sql_command_student)

    #lon_stint = 0
    #lat_stint = 0
    for coords in cursor_stint:
        lon_stint = coords[0]
        lat_stint = coords[1]
    for coords in cursor_av:
        lon_av = coords[0]
        lat_av = coords[1]
    #test = cursor_stint
    #print(test)
    #(lon_stint,lat_stint) = zip(cursor_stint[0], cursor_stint[1])
    #lon_stint = cursor_stint[0]
    #lat_stint = cursor_stint[1]
    #(lon_av,lat_av) = cursor_av

    for coor in (lon_stint,lat_stint,lon_av,lat_av):
        if coor == None:
            return numpy.nan

    R = 6365.09
    
    phi1, phi2 = math.radians(lat_stint), math.radians(lat_av)
    dphi = math.radians(lat_av - lat_stint)
    dlambda = math.radians(lon_av - lon_stint)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    
    distance = 2*R*math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return distance

def duration_stint(conn,stint_id):
    """
    Calculates duration of stint
    In:
        conn (connection) = Connection to SQL
        stint_id (int) = id of stint
    Out:
        duration_stint (int) = Duration of stint (h)
    """
    sql_command = "SELECT date_from, date_to FROM storm_stint WHERE id='{}';".format(stint_id)
    cursor_dur = conn.cursor()
    cursor_dur.execute(sql_command)
    #date_from,date_to = cursor_dur
    
    for times in cursor_dur:
        date_from = times[0]
        date_to = times[1]

    duration_stint = abs(date_to - date_from).total_seconds() / 3600.0

    return duration_stint

def duration_and_distance(conn, stint_id, student_av_id):
    """
    Calculates t/d relation of a stint.
    In:
        conn (connection) = Connection to SQL
        stint_id (int) = id of stint
        student_av_id (int) = id of student availability
    Out:
        t_and_d (float) = t/d relation
    """
    t = duration_stint(conn,stint_id)
    d = distance(conn,stint_id,student_av_id)
    try:
        t_and_d = (math.e**(-(d-1.9*t)))/(math.e**(-(d-1.9*t))+1)
        return t_and_d
    except ZeroDivisionError:
        pass
    except OverflowError:
        pass

##### WORD PROCESSING ##### not used yet

def list_raw_types(conn):
    """
    Outputs a list of all (ALL!) types of stints.

    In:
        conn (connection) = n/a
    Out:
        raw_types (list) = List of all types (strings)
    """
    cursor_type = conn.cursor()
    sql_command = "SELECT type FROM storm_stint;"
    cursor_type.execute(sql_command)
    raw_types = []
    for raw_type in cursor_type:
        if raw_type[0] not in raw_types:
            raw_types.append(raw_type[0])
    return raw_types
    
def compare_with_known_jobs(known_jobs, compare_string):
    
    """
    
    Rudimentary SpellChecker to compare a string to known, verified Jobs available in STINT.

    In:
        known_jobs (list) = A list of all verified jobs.
        compare_string (string) = The manually entered job to compare.
    Out:
        None if job is in list;
        candidates (dict) = A list of all possible words with similar spelling.
    """
    
    
    spell = SpellChecker()
    known = 0
    for item in known_jobs:
            if compare_string == item:
                    known = 1
    
    if known == 1:
            return None
    else:
        wrong = spell.unknown([compare_string])
        for word in wrong:
                candidates = spell.candidates(word)
                if candidates != None:
                        return candidates
                else:
                        return None

##### NORMALIZATION #####

def normalization(variable, constant_translation, constant_slope):
    """
    Normalizes a value.
    In:
        variable (float) = Variable to be normalized
        constant_translation (float) = Translated curve
        constant_slope (float) = Changes maximum slope
    Out:
        value (float) = Final normalized value

    """
    x = constant_slope*(variable+constant_translation)
    value = math.e**(x)/(math.e**(x)+1)
    return value

##### DESIRABILITY #####

def desirability(conn,student_id,student_av_id, stint_type,stint_id):
    """
    Calculates desirability of a student for a particular stint using our own algorithm.
    In:
        conn (connection) = Connection to SQL
        student_id (int) = id of student
        student_av_id (int) = id of student availability
        stint_type (string) = Type of stint
        stint_id (int) = id of stint

    Out:
        desirability (dict) = Dict containing student id and desirability value.
    """
    
    #if no_stints_student(conn,student_id)['number_of_stints'] <= 1:
    #    return {'student_id': student_id, 'desirability':0}

    
    grade_type_normalized = normalization(delta_grade_student_type(conn, student_id, stint_type)['mean_delta'], 0, 3)
 
    grade_general_normalized = normalization(delta_grade_student(conn, student_id)['student_grade'], 0, 3) 

    experience_type_normalized = normalization(len(same_type_stint_student(conn, student_id, stint_type)['stint_id_list']), -4, 0.8)

    experience_general_normalized = normalization(no_stints_student(conn,student_id)['number_of_stints'], -1.8, 2.8)

    distance_time_normalized = duration_and_distance(conn, stint_id, student_av_id)

    des_values = [grade_type_normalized, grade_general_normalized, experience_type_normalized, experience_general_normalized, distance_time_normalized]

    for ind in range(len(des_values)):
        if numpy.isnan(des_values[ind]):
            des_values[ind] = 0

    grade_type_normalized, grade_general_normalized, experience_type_normalized, experience_general_normalized, distance_time_normalized = tuple(des_values)

    desirability_value = ((3*grade_type_normalized + 3*experience_type_normalized + 2*grade_general_normalized + 1*distance_time_normalized)/9)*experience_general_normalized


    desirability = {'student_id': student_id, 'desirability':desirability_value}
    
    return desirability

def desirability_match(conn, business_level, desirability_list, final_list,n_max=4):
    """
    Matches student id's, according to desirability, to a business, according to its level.
    In:
        conn (connection) = Connection to SQL
        business_level (int) = Level of business
        desirability_list (list) = List of dicts of desirabilities and students id's
        stint_type (string) = Type of stint
        n_max (int) = Maximum number of stints assignable to a business. Default: 4
    Out:
        final_list (list) = List of final id's to assign to a stint
    """
    
    desirability_values = []
    for d in desirability_list:
        desirability_values.append(d['desirability'])
    desirability_max = max(desirability_values)
    
    if business_level == 4 or business_level == 5:
        for i in range(len(desirability_list)):
            if 0.75*desirability_max<=desirability_list[i]['desirability']: #the float value can be changed (0.75)
                if len(final_list) <= n_max:
                    final_list.append(desirability_list[i])
                else:
                    break

    elif business_level == 3:
        for i in range(len(desirability_list)):
            if 0.5*desirability_max<=desirability_list[i]['desirability']<0.75*desirability_max: #the float values can be changed (0.75,0.50)
                if len(final_list) <= n_max:
                    final_list.append(desirability_list[i])
                else:
                    break
                
    elif business_level == 2:
        for i in range(len(desirability_list)):
            if 0.25*desirability_max<=desirability_list[i]['desirability']<0.5*desirability_max: #the float values can be changed (0.50,0.25)
                if len(final_list) <= n_max:
                    final_list.append(desirability_list[i])
                else:
                    break
    else:
        for i in range(len(desirability_list)):
            if desirability_list[i]['desirability']<0.25*desirability_max: #the float value can be changed (0.25)
                if len(final_list) <= n_max:
                    final_list.append(desirability_list[i])
                else:
                    break
    
    return final_list

##### ALGORITHM #####

def algorithm(conn, stint_id,n_max=4):
    """
    Implementing the algorithm.
    In:
        conn (connection) = Connection to SQL
        stint_id (int) = id of stint
        n_max (int) = Max number of stints assigned to a business. Default: 4
    Out:
        final_list (list) = List of five student id's to assing to the stint
    """
    
                                        ##################################################
                                        # Use the flow diagram to follow algorithm logic #
                                        ##################################################
    
    ####################################################### Preliminary #######################################################
    
    final_list = [] #list of the final five ID
    
    sql_command = "SELECT type,business_id FROM storm_stint WHERE id='{}' AND student_id IS NOT NULL;".format(stint_id)
    cursor = conn.cursor() 
    cursor.execute(sql_command) 
    
    for cursor_element in cursor:
        stint_type = cursor_element[0] ## Fetching type of stint
        business_id = cursor_element[1] ## Fetching ID of business

    student_av = filter_available_students(conn,stint_id) # Gets students available for the stint
    
    sql_command = "SELECT ref FROM storm_business WHERE id='{}';".format(business_id)
    cursor_ref = conn.cursor()
    cursor_ref.execute(sql_command)
    for cursor_element in cursor_ref:
        business_ref = cursor_element[0]

    sql_command = "SELECT internalnote FROM storm_businesslevel WHERE uid='{}' AND internalnote IS NOT NULL;".format(business_ref)
    cursor_level = conn.cursor()
    cursor_level.execute(sql_command)
    for cursor_element_level in cursor_level:
        business_level = cursor_element_level[0] ## Fetching level of business (STINT Ranking)
    
    ##################################################  Treat special business cases ###################################################
    
    if no_stints_business(conn, business_id)['number_of_stints'] < 5:
        business_level = 4 # MAKES IT SO THAT BEGINNER BUSINESSES GET THE BEST TREATMENT POSSIBLE
    if business_level == None:
        business_level = 3 # MAKES IT SO THAT 'UNLABELLED' BUSINESSES GET TREATED AS AN AVERAGE BUSINESS

    ############################################### Calculation of the list of desirabilities ###########################################

    desirability_list = [] ## To be populated by algorithm. This list is the one with the potential choices in the end
    
    for obj in student_av: # Adds 'desirability dicts' to the 'desirability_list'
        desirability_list.append(desirability(conn,obj['student_id'],obj['student_av_id'],stint_type,stint_id))
    
    desirability_list = sorted(desirability_list,key=lambda k: k['desirability'],reverse=True) # Sorts desirability list

    if business_level == 3:
        chosen_students = []
        for i in range(len(student_av)):
            try:
                random_student_id = random.choice(set(student_av).difference(set(chosen_students)))
            except:
                continue
            if random_student_id not in chosen_students:
                chosen_students.append(random_student_id)
                if no_stints_student(conn, random_student_id) < 3:
                    final_list.append(random_student_id)
                    break
    
    ########################################################## Check if they worked together ###########################################################
    
    temp_list = []
    for obj in student_av:### CHECK IF STUDENT(S) HAS(HAVE) WORKED WITH BUSINESS BEFORE
        stint_connection = stint_student_business(conn, business_id, obj['student_id'])
        if stint_connection["worked_together"] is True:
            grade_list = []
            for stint_id in stint_connection["stint_id_list"]:
                cursor = conn.cursor()
                sql_command = "SELECT grade FROM storm_review WHERE stint_id='{}' AND grade IS NOT NULL;".format(stint_id[0])
                cursor.execute(sql_command)
                for obj in cursor:
                    grade_list.append(obj[0])
            if grade_list == []:
                break
            else:
                if numpy.mean(grade_list) > average_business_rating(conn, business_id)['mean_grade']:
                    temp_list.append(stint_connection["student_id"])

    try:
        for j in range(3):
            final_list.append(temp_list.pop(random.randint(0,len(temp_list))))
    except:
        pass

    ############################################ Ensuring max number 'n_max' of elements in final list ####################################################


    final_list = desirability_match(conn, business_level, desirability_list, final_list)
    
    for i in range(3):
        if len(final_list)<n_max:
            if business_level == 4:
                business_level = 3
                final_list = desirability_match(conn, business_level, desirability_list, final_list)
            elif business_level != 4:
                business_level = business_level+1
                final_list = desirability_match(conn, business_level, desirability_list, final_list)
            else:
                pass
        else:
            pass
        
    if len(final_list)<n_max:
        chosen_students = []
        for i in range(len(student_av)):
            try:
                random_student_id = random.choice(set(student_available).difference(set(chosen_students)))
            except:
                continue
            if random_student_id not in chosen_students:
                chosen_students.append(random_student_id)
                final_list.append(random_student_id)
                break
    
    output = {"stint_id":stint_id,"business_level":business_level,"final_list_id":final_list}
        
    return output

##### MAIN #####

def main(stint_id=None):
    """
    Main function. Can also be imported and used in another file (specifying 'stint_id')
    In:
        stint_id (int) = id of stint. Optional value to add when calling the function
    Out:
        final (list) = List of student id's for the stint
    """
    conn = psycopg2.connect("host=localhost port=5432 dbname=hackathon user=postgres password=habbothink11") # Remember to change this the right values

    ##### Function can be customized under here #####
    #                                               #
    #  As is it right now, the function needs to be #
    #  called with a specified stint_id, for ease   #
    #  of use as an importable function, like this: #
    #  main(stint_id=<DESIDERED_STINT_ID>), with    #
    #  your desired id (int).                       #
    #  To use as standalone, just either define a   #
    #  variable 'stint_id' with the wanted id, or   #
    #  iter over them as you need/please.           #
    #                                               #
    ##### Function can be customized above here #####
    
    final = algorithm(conn, stint_id)
    print(final)

    conn = None
    
    return final

main(stint_id=7666)
